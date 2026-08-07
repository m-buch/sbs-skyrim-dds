#include "Encode.h"

#include <bc7enc.h>
#include <rgbcx.h>

#include <algorithm>
#include <cstring>
#include <mutex>
#include <thread>

namespace skydds
{

namespace
{

const std::uint32_t bc1QualityLevel = 10;
const std::uint8_t alphaTestThreshold = 128;

void initEncodersOnce()
{
	static std::once_flag once;
	std::call_once(once, []
	{
		rgbcx::init();
		bc7enc_compress_block_init();
	});
}

// Copies the 4x4 block at (bx, by)
void extractBlock(const ImageRGBA& image, unsigned int bx, unsigned int by,
	std::uint8_t out[64])
{
	for (unsigned int y = 0; y < 4; ++y)
	{
		unsigned int sy = std::min(by*4 + y, image.height - 1);
		for (unsigned int x = 0; x < 4; ++x)
		{
			unsigned int sx = std::min(bx*4 + x, image.width - 1);
			std::memcpy(out + (y*4 + x)*4, image.pixels.data() + (sy*image.width + sx)*4, 4);
		}
	}
}

std::uint16_t to565(const std::uint8_t* rgb)
{
	return static_cast<std::uint16_t>(((rgb[0] >> 3) << 11) | ((rgb[1] >> 2) << 5) | (rgb[2] >> 3));
}

void from565(std::uint16_t color, int out[3])
{
	int r = (color >> 11) & 31;
	int g = (color >> 5) & 63;
	int b = color & 31;
	out[0] = (r << 3) | (r >> 2);
	out[1] = (g << 2) | (g >> 4);
	out[2] = (b << 3) | (b >> 2);
}

// BC1 with 1-bit punch-through alpha. rgbcx has no punch-through support, so
// transparent blocks use our own encoder: 3-color mode (color0 <= color1) with
// selector 3 for transparent texels. Opaque blocks go through rgbcx restricted
// to 4-color mode so no selector ever decodes transparent.
void encodeBc1aBlock(std::uint8_t* dst, const std::uint8_t pixels[64])
{
	std::uint32_t transparentMask = 0;
	for (unsigned int i = 0; i < 16; ++i)
	{
		if (pixels[i*4 + 3] < alphaTestThreshold)
			transparentMask |= 1u << i;
	}

	if (!transparentMask)
	{
		rgbcx::encode_bc1(bc1QualityLevel, dst, pixels, false, false);
		return;
	}

	// Endpoints: bounding box of the opaque texels' colors.
	std::uint8_t minColor[3] = {255, 255, 255};
	std::uint8_t maxColor[3] = {0, 0, 0};
	for (unsigned int i = 0; i < 16; ++i)
	{
		if (transparentMask & (1u << i))
			continue;
		for (unsigned int c = 0; c < 3; ++c)
		{
			minColor[c] = std::min(minColor[c], pixels[i*4 + c]);
			maxColor[c] = std::max(maxColor[c], pixels[i*4 + c]);
		}
	}
	if (transparentMask == 0xFFFF)
	{
		minColor[0] = minColor[1] = minColor[2] = 0;
		maxColor[0] = maxColor[1] = maxColor[2] = 0;
	}

	std::uint16_t color0 = to565(minColor);
	std::uint16_t color1 = to565(maxColor);
	// 3-color mode requires color0 <= color1.
	if (color0 > color1)
		std::swap(color0, color1);

	int palette[3][3];
	from565(color0, palette[0]);
	from565(color1, palette[1]);
	for (unsigned int c = 0; c < 3; ++c)
		palette[2][c] = (palette[0][c] + palette[1][c])/2;

	std::uint32_t selectors = 0;
	for (unsigned int i = 0; i < 16; ++i)
	{
		std::uint32_t selector = 3;
		if (!(transparentMask & (1u << i)))
		{
			std::uint32_t best = 0;
			int bestError = INT32_MAX;
			for (std::uint32_t p = 0; p < 3; ++p)
			{
				int error = 0;
				for (unsigned int c = 0; c < 3; ++c)
				{
					int d = static_cast<int>(pixels[i*4 + c]) - palette[p][c];
					error += d*d;
				}
				if (error < bestError)
				{
					bestError = error;
					best = p;
				}
			}
			selector = best;
		}
		selectors |= selector << (i*2);
	}

	dst[0] = static_cast<std::uint8_t>(color0);
	dst[1] = static_cast<std::uint8_t>(color0 >> 8);
	dst[2] = static_cast<std::uint8_t>(color1);
	dst[3] = static_cast<std::uint8_t>(color1 >> 8);
	std::memcpy(dst + 4, &selectors, 4);
}

void encodeBlock(std::uint8_t* dst, const std::uint8_t pixels[64], BlockFormat format,
	const bc7enc_compress_block_params& bc7Params)
{
	switch (format)
	{
		case BlockFormat::BC1:
			rgbcx::encode_bc1(bc1QualityLevel, dst, pixels, true, false);
			break;
		case BlockFormat::BC1a:
			encodeBc1aBlock(dst, pixels);
			break;
		case BlockFormat::BC4:
			rgbcx::encode_bc4(dst, pixels, 4);
			break;
		case BlockFormat::BC7:
			bc7enc_compress_block(dst, pixels, &bc7Params);
			break;
	}
}

} // namespace

std::vector<std::uint8_t> encodeImage(const ImageRGBA& image, BlockFormat format,
	bool perceptual, unsigned int threads)
{
	initEncodersOnce();

	bc7enc_compress_block_params bc7Params;
	bc7enc_compress_block_params_init(&bc7Params);
	if (!perceptual)
		bc7enc_compress_block_params_init_linear_weights(&bc7Params);

	unsigned int blocksX = (image.width + 3)/4;
	unsigned int blocksY = (image.height + 3)/4;
	unsigned int bytes = blockBytes(format);
	std::vector<std::uint8_t> result(static_cast<std::size_t>(blocksX)*blocksY*bytes);

	if (threads == 0)
		threads = std::thread::hardware_concurrency();
	threads = std::max(1u, std::min(threads, blocksY));

	auto encodeRows = [&](unsigned int beginRow, unsigned int endRow)
	{
		std::uint8_t pixels[64];
		for (unsigned int by = beginRow; by < endRow; ++by)
		{
			for (unsigned int bx = 0; bx < blocksX; ++bx)
			{
				extractBlock(image, bx, by, pixels);
				encodeBlock(result.data() + (static_cast<std::size_t>(by)*blocksX + bx)*bytes,
					pixels, format, bc7Params);
			}
		}
	};

	if (threads == 1)
		encodeRows(0, blocksY);
	else
	{
		std::vector<std::thread> workers;
		workers.reserve(threads);
		unsigned int rowsPerThread = (blocksY + threads - 1)/threads;
		for (unsigned int t = 0; t < threads; ++t)
		{
			unsigned int begin = t*rowsPerThread;
			unsigned int end = std::min(begin + rowsPerThread, blocksY);
			if (begin >= end)
				break;
			workers.emplace_back(encodeRows, begin, end);
		}
		for (std::thread& worker : workers)
			worker.join();
	}
	return result;
}

} // namespace skydds
