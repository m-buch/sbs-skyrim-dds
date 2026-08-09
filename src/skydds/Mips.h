#pragma once

#include "ImageRGBA.h"

#include <vector>

namespace skydds
{

// Number of mip levels for a full chain down to 1x1
unsigned int mipLevelCount(unsigned int width, unsigned int height);

// Resizes an image. sRGB inputs are gamma corrected.
// Support for alpha premult when generating mipmaps for transparent textures
ImageRGBA resizeImage(const ImageRGBA& image, unsigned int width, unsigned int height, bool srgb,
	bool alphaWeighted);

// Builds mipmaps of levels "levels" with idx 0 being base
std::vector<ImageRGBA> buildMipChain(ImageRGBA base, unsigned int levels, bool srgb,
	bool alphaWeighted);

// Fraction of texels that would pass an alphaRef alpha test
double alphaCoverage(const ImageRGBA& image, double alphaRef, double scale = 1.0);

// Rescales each mip's alpha so the same fraction of texels passes the alpha
// test as at level 0
void preserveAlphaCoverage(std::vector<ImageRGBA>& chain, double alphaRef);

} // namespace skydds
