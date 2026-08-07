#include "Dds.h"

#include <cstring>
#include <fstream>

namespace skydds
{

namespace
{

struct Writer
{
	std::ofstream file;

	void u32(std::uint32_t value)
	{
		file.write(reinterpret_cast<const char*>(&value), 4);
	}
};

} // namespace

bool writeDds(const std::string& path, BlockFormat format,
	const std::vector<EncodedLevel>& levels)
{
	if (levels.empty())
		return false;

	Writer out;
	out.file.open(path, std::ios::binary);
	if (!out.file)
		return false;

	const std::uint32_t ddsdCaps = 0x1;
	const std::uint32_t ddsdHeight = 0x2;
	const std::uint32_t ddsdWidth = 0x4;
	const std::uint32_t ddsdPixelFormat = 0x1000;
	const std::uint32_t ddsdMipMapCount = 0x20000;
	const std::uint32_t ddsdLinearSize = 0x80000;
	const std::uint32_t ddscapsComplex = 0x8;
	const std::uint32_t ddscapsTexture = 0x1000;
	const std::uint32_t ddscapsMipMap = 0x400000;
	const std::uint32_t ddpfFourCC = 0x4;

	const EncodedLevel& top = levels[0];
	std::uint32_t mipCount = static_cast<std::uint32_t>(levels.size());
	std::uint32_t linearSize = static_cast<std::uint32_t>(top.blocks.size());

	out.file.write("DDS ", 4);
	// DDS_HEADER
	out.u32(124); // dwSize
	std::uint32_t flags = ddsdCaps | ddsdHeight | ddsdWidth | ddsdPixelFormat | ddsdLinearSize;
	if (mipCount > 1)
		flags |= ddsdMipMapCount;
	out.u32(flags);
	out.u32(top.height);
	out.u32(top.width);
	out.u32(linearSize);
	out.u32(0); // dwDepth
	out.u32(mipCount);
	for (int i = 0; i < 11; ++i)
		out.u32(0); // dwReserved1
	// DDS_PIXELFORMAT
	out.u32(32); // dwSize
	out.u32(ddpfFourCC);
	out.file.write("DX10", 4);
	for (int i = 0; i < 5; ++i)
		out.u32(0); // RGB bit counts/masks
	std::uint32_t caps = ddscapsTexture;
	if (mipCount > 1)
		caps |= ddscapsComplex | ddscapsMipMap;
	out.u32(caps);
	out.u32(0); // dwCaps2
	out.u32(0);
	out.u32(0);
	out.u32(0); // dwReserved2
	// DDS_HEADER_DXT10
	out.u32(dxgiFormat(format));
	out.u32(3); // D3D10_RESOURCE_DIMENSION_TEXTURE2D
	out.u32(0); // miscFlag
	out.u32(1); // arraySize
	out.u32(0); // miscFlags2: alpha mode Unknown, matching vanilla

	for (const EncodedLevel& level : levels)
	{
		out.file.write(reinterpret_cast<const char*>(level.blocks.data()),
			static_cast<std::streamsize>(level.blocks.size()));
	}
	return static_cast<bool>(out.file);
}

} // namespace skydds
