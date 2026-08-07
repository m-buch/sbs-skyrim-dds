#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace skydds
{

struct ImageRGBA
{
	unsigned int width = 0;
	unsigned int height = 0;
	std::vector<std::uint8_t> pixels; // width*height*4

	bool isValid() const { return width > 0 && height > 0; }
};

// Loads any stb_image-supported file forcing RGBA8.
// Returns an invalid image on failure.
ImageRGBA loadImage(const std::string& path);

} // namespace skydds
