#include "ImageRGBA.h"

#include <stb_image.h>

#include <cstring>

namespace skydds
{

ImageRGBA loadImage(const std::string& path)
{
	ImageRGBA image;
	int width = 0;
	int height = 0;
	int channels = 0;
	stbi_uc* data = stbi_load(path.c_str(), &width, &height, &channels, 4);
	if (!data)
		return image;

	image.width = static_cast<unsigned int>(width);
	image.height = static_cast<unsigned int>(height);
	image.pixels.resize(image.width*image.height*4);
	std::memcpy(image.pixels.data(), data, image.pixels.size());
	stbi_image_free(data);
	return image;
}

} // namespace skydds
