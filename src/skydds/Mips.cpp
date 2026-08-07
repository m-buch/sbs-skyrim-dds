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

	void* ok = stbir_resize(image.pixels.data(), static_cast<int>(image.width),
		static_cast<int>(image.height), 0, result.pixels.data(), static_cast<int>(width),
		static_cast<int>(height), 0, alphaWeighted ? STBIR_RGBA : STBIR_4CHANNEL,
		srgb ? STBIR_TYPE_UINT8_SRGB : STBIR_TYPE_UINT8, STBIR_EDGE_CLAMP,
		STBIR_FILTER_CATMULLROM);
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

} // namespace skydds
