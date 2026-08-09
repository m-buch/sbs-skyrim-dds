#include "Mips.h"

#include <stb_image_resize2.h>

#include <utility>

namespace skydds
{

unsigned int mipLevelCount(unsigned int width, unsigned int height)
{
	unsigned int maxDim = width > height ? width : height;
	unsigned int levels = 1;
	while (maxDim > 1)
	{
		maxDim >>= 1;
		++levels;
	}
	return levels;
}

ImageRGBA resizeImage(const ImageRGBA& image, unsigned int width, unsigned int height, bool srgb,
	bool alphaWeighted)
{
	ImageRGBA result;
	result.width = width;
	result.height = height;
	result.pixels.resize(width*height*4);

	stbir_pixel_layout layout = alphaWeighted ? STBIR_RGBA : STBIR_RGBA_NO_AW;
	void* ok = stbir_resize(image.pixels.data(), static_cast<int>(image.width),
		static_cast<int>(image.height), 0, result.pixels.data(), static_cast<int>(width),
		static_cast<int>(height), 0, layout,
		srgb ? STBIR_TYPE_UINT8_SRGB : STBIR_TYPE_UINT8, STBIR_EDGE_CLAMP,
		// switched to Box for now. Mitchell/Kaiser etc. have weird behavior
		// with premultiplied alpha because of negative lobes
		STBIR_FILTER_BOX);
	if (!ok)
		result = ImageRGBA();
	return result;
}

std::vector<ImageRGBA> buildMipChain(ImageRGBA base, unsigned int levels, bool srgb,
	bool alphaWeighted)
{
	std::vector<ImageRGBA> chain;
	chain.reserve(levels);
	for (unsigned int i = 1; i < levels; ++i)
	{
		unsigned int width = base.width >> i;
		unsigned int height = base.height >> i;
		if (width == 0)
			width = 1;
		if (height == 0)
			height = 1;
		chain.push_back(resizeImage(base, width, height, srgb, alphaWeighted));
	}
	chain.insert(chain.begin(), std::move(base));
	return chain;
}

double alphaCoverage(const ImageRGBA& image, double alphaRef, double scale)
{
	if (image.pixels.empty())
		return 0.0;

	std::size_t passed = 0;
	std::size_t total = 0;
	for (std::size_t i = 3; i < image.pixels.size(); i += 4)
	{
		if (image.pixels[i]*scale/255.0 >= alphaRef)
			++passed;
		++total;
	}
	return total ? static_cast<double>(passed)/static_cast<double>(total) : 0.0;
}

// Based on Ignacio Castaño's alpha to coverage technique
void preserveAlphaCoverage(std::vector<ImageRGBA>& chain, double alphaRef)
{
	if (chain.size() < 2)
		return;

	double target = alphaCoverage(chain[0], alphaRef);
	if (target <= 0.0 || target >= 1.0)
		return;

	for (std::size_t level = 1; level < chain.size(); ++level)
	{
		ImageRGBA& mip = chain[level];
		if (mip.pixels.empty())
			continue;

		double low = 0.0;
		double high = 8.0;
		for (int step = 0; step < 16; ++step)
		{
			double scale = (low + high)*0.5;
			if (alphaCoverage(mip, alphaRef, scale) < target)
				low = scale;
			else
				high = scale;
		}
		double scale = high;

		for (std::size_t i = 3; i < mip.pixels.size(); i += 4)
		{
			double alpha = mip.pixels[i]*scale;
			if (alpha > 255.0)
				alpha = 255.0;
			mip.pixels[i] = static_cast<std::uint8_t>(alpha + 0.5);
		}
	}
}

} // namespace skydds
