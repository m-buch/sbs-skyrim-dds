#pragma once

#include "Format.h"
#include "SlotTable.h"

#include <string>

namespace skydds
{

enum class AlphaMode
{
	Auto,  // detect from image content
	None,  // ignore alpha
	Blend, // alpha blended
	Test   // alpha tested 1-bit alpha format
};

struct ExportRequest
{
	std::string inputPath;
	std::string outputPath;
	const Slot* slot = nullptr;
	AlphaMode alphaMode = AlphaMode::Auto;
	bool resizePow2 = false;
	bool dryRun = false;
	unsigned int threads = 0; // 0 = use all
};

struct ExportResult
{
	bool success = false;
	std::string error; // set when !success

	// Resolved settings
	BlockFormat format = BlockFormat::BC1;
	unsigned int width = 0;
	unsigned int height = 0;
	unsigned int mipLevels = 0;

	// Alpha when AlphaMode::Auto
	bool alphaScanned = false;
	unsigned int nonOpaqueTexels = 0;
	unsigned int minAlpha = 255;
};

ExportResult exportTexture(const ExportRequest& request);

} // namespace skydds
