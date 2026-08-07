#pragma once

#include "Format.h"
#include "ImageRGBA.h"

#include <cstdint>
#include <vector>

namespace skydds
{

// Encodes one image to BC blocks
std::vector<std::uint8_t> encodeImage(const ImageRGBA& image, BlockFormat format,
	bool perceptual, unsigned int threads);

} // namespace skydds
