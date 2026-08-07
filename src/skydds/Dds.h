#pragma once

#include "Format.h"

#include <cstdint>
#include <string>
#include <vector>

namespace skydds
{

struct EncodedLevel
{
	unsigned int width = 0;
	unsigned int height = 0;
	std::vector<std::uint8_t> blocks;
};

// Writes a 2D DDS with a DX10 extended header
bool writeDds(const std::string& path, BlockFormat format,
	const std::vector<EncodedLevel>& levels);

} // namespace skydds
