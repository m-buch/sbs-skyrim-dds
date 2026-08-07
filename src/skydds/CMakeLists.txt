set(externalDir ${CMAKE_SOURCE_DIR}/external)

add_library(skydds_core STATIC
	Dds.cpp
	Dds.h
	Encode.cpp
	Encode.h
	Export.cpp
	Export.h
	Format.h
	ImageIO.cpp
	ImageRGBA.h
	Mips.cpp
	Mips.h
	StbImpl.cpp
	${externalDir}/bc7enc_rdo/bc7enc.cpp
	${externalDir}/bc7enc_rdo/rgbcx.cpp
)
target_compile_features(skydds_core PUBLIC cxx_std_17)
target_include_directories(skydds_core
	PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/..
	PRIVATE ${externalDir}/bc7enc_rdo ${externalDir}/stb
)
if (MSVC)
	set_source_files_properties(
		${externalDir}/bc7enc_rdo/bc7enc.cpp
		${externalDir}/bc7enc_rdo/rgbcx.cpp
		PROPERTIES COMPILE_OPTIONS /w)
endif()
