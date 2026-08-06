add_executable(skydds main.cpp)
target_compile_features(skydds PRIVATE cxx_std_17)
target_link_libraries(skydds PRIVATE cuttlefish_lib)
