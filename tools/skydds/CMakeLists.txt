add_executable(skydds main.cpp Cli.cpp Cli.h)
target_compile_features(skydds PRIVATE cxx_std_17)
target_link_libraries(skydds PRIVATE skydds_core)
