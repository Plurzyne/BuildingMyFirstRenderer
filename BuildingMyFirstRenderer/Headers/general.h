#ifndef GENERAL_H
#define GENERAL_H

#include <cmath>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <memory>
#include <random>
#include <fstream>
#include <string>
#include <vector>

// C++ Std Usings

using std::make_shared;
using std::shared_ptr;

// Constants

const double infinity = std::numeric_limits<double>::infinity();
const double pi = 3.1415926535897932385;

// Utility Functions

inline double degrees_to_radians(double degrees) {
    return degrees * pi / 180.0;
}

inline std::mt19937& rng() {
    static std::mt19937 generator;
    return generator;
}

inline void set_seed(unsigned int seed) {
    rng().seed(seed);
}

inline double random_double() {
    static std::uniform_real_distribution<double> distribution(0.0, 1.0);
    return distribution(rng());
}

inline double random_double(double min, double max) {
    // Returns a random real in [min,max).
    return min + (max - min) * random_double();
}

// Common Headers

#include "color.h"
#include "interval.h"
#include "ray.h"
#include "vec3.h"

#endif