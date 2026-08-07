#pragma once

#include <cstdint>

namespace skydds
{

enum class BlockFormat
{
	BC1,
	BC1a,
	BC4,
	BC7
};

enum class AlphaKind
{
	None,     // no alpha
	Standard, // transparency
	Encoded   // data packed (f.e. specularity)
};

inline unsigned int blockBytes(BlockFormat format)
{
	return format == BlockFormat::BC7 ? 16 : 8;
}

// DXGI_FORMAT always _UNORM as in base game textures
inline std::uint32_t dxgiFormat(BlockFormat format)
{
	switch (format)
	{
		case BlockFormat::BC1:
		case BlockFormat::BC1a:
			return 71; // DXGI_FORMAT_BC1_UNORM
		case BlockFormat::BC4:
			return 80; // DXGI_FORMAT_BC4_UNORM
		default:
			return 98; // DXGI_FORMAT_BC7_UNORM
	}
}

inline bool formatHasAlpha(BlockFormat format)
{
	return format == BlockFormat::BC1a || format == BlockFormat::BC7;
}

inline const char* formatName(BlockFormat format)
{
	switch (format)
	{
		case BlockFormat::BC1:
			return "BC1";
		case BlockFormat::BC1a:
			return "BC1a";
		case BlockFormat::BC4:
			return "BC4";
		default:
			return "BC7";
	}
}

} // namespace skydds
