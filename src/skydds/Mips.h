#pragma once

#include "ImageRGBA.h"

#include <vector>

namespace skydds
{

// Number of mip levels for a full chain down to 1x1
unsigned int mipLevelCount(unsigned int width, unsigned int height);

// Resizes an image. sRGB inputs are gamma corrected.
// alphaWeighted filters for alpha coverage (for transparent things like foliage)
// do not use alphaWeighted for non-encoded alpha ie. specular maps etc
ImageRGBA resizeImage(const ImageRGBA& image, unsigned int width, unsigned int height, bool srgb,
	bool alphaWeighted);

// Builds mipmaps of levels "levels" with idx 0 being base
std::vector<ImageRGBA> buildMipChain(ImageRGBA base, unsigned int levels, bool srgb,
	bool alphaWeighted);

} // namespace skydds
