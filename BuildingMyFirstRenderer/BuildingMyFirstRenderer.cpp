#include "Headers/general.h"
#include "Headers/camera.h"
#include "Headers/hittable.h"
#include "Headers/hittable_list.h"
#include "Headers/material.h"
#include "Headers/sphere.h"

int main(int argc, char* argv[]) {
    hittable_list world;

    auto material_ground = make_shared<lambertian>(color(0.8, 0.8, 0.0));
    auto material_center = make_shared<lambertian>(color(0.1, 0.2, 0.5));
    auto material_left = make_shared<dielectric>(1.50);
    auto material_bubble = make_shared<dielectric>(1.00 / 1.50);
    auto material_right = make_shared<metal>(color(0.8, 0.6, 0.2), 1.0);

    material_ground->id = 1;
    material_center->id = 2;
    material_left->id = 3;
    material_bubble->id = 3;   // the bubble is part of the glass sphere
    material_right->id = 4;

    world.add(make_shared<sphere>(point3( 0.0, -100.5, -1.0), 100.0, material_ground));
    world.add(make_shared<sphere>(point3( 0.0,    0.0, -1.2),   0.5, material_center));
    world.add(make_shared<sphere>(point3(-1.0,    0.0, -1.0),   0.5, material_left));
    world.add(make_shared<sphere>(point3(-1.0, 0.0, -1.0), 0.4, material_bubble));
    world.add(make_shared<sphere>(point3( 1.0,    0.0, -1.0),   0.5, material_right));

    camera cam;

    cam.aspect_ratio = 16.0 / 9.0;
    cam.image_width = 400;
    cam.samples_per_pixel = 100;
    cam.max_depth = 50;

    if (argc >= 4) {
        cam.samples_per_pixel = std::stoi(argv[1]);
        set_seed(std::stoi(argv[2]));
        cam.float_output_path = argv[3];
    }

    if (argc >= 5) {
        cam.id_output_path = argv[4];
    }

    cam.render(world);
}