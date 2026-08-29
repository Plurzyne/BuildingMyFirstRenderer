# Ray Tracer — Working Notes

Reference notes for `BuildingMyFirstRenderer`, following *Ray Tracing in One Weekend* (Peter Shirley).

**Coverage:** up to and including antialiasing / the `camera` class. Diffuse materials not yet added.

---

## 1. What this program does

Ray tracing runs light transport **backwards**. Instead of following photons from a light source and hoping they reach the eye (almost none do), rays start at the camera and travel outward into the scene. Every ray traced is one that matters.

The whole program is:

> For each pixel: work out what you'd see looking through it, and write down that colour.

Everything else is machinery serving that loop.

---

## 2. File map

```
general.h        hub — std includes, constants, utility functions
 ├── vec3.h      3-component vector: position, direction, colour
 ├── ray.h       parametrised line P(t) = Q + t·d
 ├── color.h     [0,1] colour → PPM byte output
 └── interval.h  a [min, max] range with containment tests

hittable.h       abstract interface + hit_record
 ├── sphere.h        implements hittable
 └── hittable_list.h implements hittable, holds a vector of hittables

camera.h         viewport setup, pixel loop, antialiasing, ray_color
main.cpp         builds the world, configures the camera, calls render()
```

**Key dependency:** `main.cpp` depends on `hittable`, never on `sphere`. `ray_color` calls `world.hit(...)` and has no idea what's in the scene. That indirection is the architectural payoff of the hittable design.

### Include hygiene (outstanding issue)

`hittable.h`, `sphere.h`, and `hittable_list.h` do not include `general.h`. They compile only because `main.cpp` includes `general.h` first. Change the include order and the build breaks. Fix: add `#include "general.h"` at the top of each.

---

## 3. Coordinate conventions

Right-handed system:

| axis | direction |
|---|---|
| +x | right |
| +y | up |
| −z | into the screen (camera looks this way) |

**Conflicting convention:** image coordinates put pixel (0,0) at the **top-left**, with `j` increasing *downward*. World y increases *upward*. These are reconciled by making `viewport_v` negative:

```cpp
auto viewport_v = vec3(0, -viewport_height, 0);
```

The sign is handled once, here, so `j` can count up normally in the loop.

### Units

There are none. All distances are bare `double`s. Only **ratios** matter — scale the whole scene by 1000× and the image is identical. Keep objects roughly unit-sized (0.1 to 100) so floating-point behaves well.

---

## 4. `vec3` — the arithmetic layer

One class, three roles: **position** (`point3`), **direction**, and **colour** (`color`). Both aliases are `using` declarations — same type, different names, purely for readability.

```cpp
double e[3];   // 24 bytes, no allocation
```

### Members

| member | notes |
|---|---|
| `x() y() z()` | named component access, all `const` |
| `operator-()` | unary negation, returns a new vec3 |
| `operator[]` ×2 | const version returns a copy; non-const returns `double&` (writable) |
| `operator+= *= /=` | modify in place, return `*this` as `vec3&` for chaining |
| `length()` | `sqrt(length_squared())` |
| `length_squared()` | public because comparisons often don't need the sqrt |

`operator/=` computes `1/t` once and multiplies — one division instead of three.

### Free functions (all `inline`)

`inline` here is about **linkage**, not optimisation: it lets the same definition appear in multiple translation units without a linker error.

| function | notes |
|---|---|
| `operator<<` | stream output; must be free (left operand is a stream) |
| `operator+ -` | component-wise |
| `operator*(vec3, vec3)` | **component-wise, NOT dot product** — this is for colour attenuation |
| `operator*(double, vec3)` and `(vec3, double)` | two overloads because C++ matches by position |
| `dot(u,v)` | returns a **scalar**; `= |u||v|cos θ`. The most-used function in the renderer |
| `cross(u,v)` | returns a **vector** perpendicular to both; used for camera basis |
| `unit_vector(v)` | `v / v.length()` |

---

## 5. `ray`

**P(t) = Q + t·d** — origin plus t times direction.

```cpp
point3 at(double t) const { return orig + t * dir; }
```

- `t > 0` → forward (visible)
- `t < 0` → backward, behind the camera (invisible, but the maths still solves for it)

Members are `private`; accessors return `const point3&` — reference to avoid copying 24 bytes, `const` so callers can't write into a private member.

**Directions are not normalised.** Since the direction spans camera→viewport at distance 1, `t = 1` lands on the viewport plane. This matters when interpreting what `t` means.

---

## 6. Colour and PPM output

Colours are `double` in **[0,1]**, converted to bytes only at output.

```cpp
int rbyte = int(255.999 * r);
```

**Why 255.999?** `int(...)` truncates. Using 255 would make bucket 255 hit only at exactly `r == 1.0` (biased). Using 256 would produce 256 for `r == 1.0` (out of range). 255.999 gives 256 even buckets with a max of 255.

**Note:** `write_color` is missing `inline`. Works with one `.cpp` file; will cause `LNK2005` if a second one includes `color.h`.

### Running it

```
x64\Debug\BuildingMyFirstRenderer.exe > image.ppm
```

In **cmd**, plain `>` is raw byte redirection — fine. In **PowerShell**, `>` writes UTF-16 and corrupts the file; use `cmd /c "... > image.ppm"` instead.

Progress output goes to `std::clog`, not `std::cout`, so it doesn't land inside the image data.

---

## 7. The camera model

### The viewport

A rectangle floating in space in front of the camera, subdivided into the same grid as the image. Pixel (i,j) maps to a point on it; the ray goes from the camera through that point.

**The viewport is not an object.** Not glass, not a wall. It blocks nothing. It exists for exactly two lines:

```cpp
auto pixel_center = pixel00_loc + (i * pixel_delta_u) + (j * pixel_delta_v);
auto ray_direction = pixel_sample - ray_origin;
```

After `ray_direction` is computed, the viewport is never referenced again. `hit_sphere` has no idea it exists. Objects can sit in front of it, behind it, or straddling it — nothing breaks.

Think of it as a protractor: used to aim, then put away.

### Field of view

FOV ∝ `viewport_height / focal_length`. **Only the ratio matters** — doubling both changes nothing.

Default: half-height 1.0 at distance 1.0 → 45° each way → **90° vertical FOV**.

| change | effect |
|---|---|
| ↑ focal_length | narrower cone → **things look BIGGER** (telephoto) |
| ↑ viewport_height | wider cone → things look smaller (wide-angle) |

**Narrow FOV = magnification.** A telescope has a tiny FOV and makes the moon look huge. Less world captured, spread over the same pixel grid.

Worked example — how much world is visible at z = −1 (the sphere's depth):

| focal_length | visible height at z=−1 | sphere (1.0 tall) fills |
|---|---|---|
| 1.0 | 2.0 units | half the frame |
| 2.0 | 1.0 unit | the whole frame |

### Why the image is 2D

The scene is all of infinite 3D space. The image is 2D because the **sampling pattern** is 2D — a 400×225 grid of directions, each returning one colour. Same reason a camera sensor produces a rectangle.

Two stages: **choose a cone** (FOV), then **sample it on a grid** (resolution). Independent knobs.

### Setup arithmetic

```cpp
viewport_width = viewport_height * (double(image_width) / image_height);
```

Guarantees **square pixels** — `pixel_delta_u` and `pixel_delta_v` end up the same magnitude. Uses the actual integer dimensions, not `aspect_ratio`, because `image_height` was truncated.

```cpp
pixel_delta_u = viewport_u / image_width;    // world-space step, one pixel right
pixel_delta_v = viewport_v / image_height;   // one pixel down

viewport_upper_left = center - vec3(0,0,focal_length) - viewport_u/2 - viewport_v/2;
pixel00_loc = viewport_upper_left + 0.5 * (pixel_delta_u + pixel_delta_v);
```

The `0.5 *` step moves from the rectangle's **corner** to the first pixel's **centre**. Matters once samples are jittered within pixels.

Subtracting `viewport_v/2` **adds** to y (because `viewport_v` is negative) — moves up to the top edge.

`image_height` is clamped to ≥ 1 so the row loop always executes and `image_height - 1` never goes negative.

### Pixel index → 3D position

Like a theatre seat: "row 12, seat 7" identifies a physical location given (a) where seat (0,0) is, (b) seat spacing, (c) row spacing.

| theatre | code |
|---|---|
| seat (0,0) position | `pixel00_loc` |
| sideways spacing | `pixel_delta_u` |
| row spacing | `pixel_delta_v` |

Two integers in → one 3D point out → subtract camera position → direction.

---

## 8. Ray–sphere intersection

Substituting P(t) into the sphere equation gives a quadratic in t:

**(d·d)t² − 2(d·oc)t + (oc·oc − r²) = 0**,  where **oc = C − Q**

### Simplified form

Setting `h = d·oc` (so `b = −2h`), every factor of 2 and 4 cancels:

```cpp
auto a = r.direction().length_squared();
auto h = dot(r.direction(), oc);
auto c = oc.length_squared() - radius*radius;
auto discriminant = h*h - a*c;         // was b*b - 4*a*c
auto root = (h - sqrtd) / a;           // was (-b - sqrt(...)) / (2a)
```

Value changes but the **sign** doesn't, which is all that's tested.

### Interpreting the coefficients

| quantity | meaning |
|---|---|
| `c > 0` | camera **outside** the sphere |
| `c < 0` | camera **inside** — then `−4ac > 0`, discriminant always ≥ 0, **every ray hits** (correct: inside a sphere, every direction meets the wall) |
| discriminant < 0 | line misses entirely |
| discriminant = 0 | tangent |
| discriminant > 0 | enters and exits |

### The near/far root check

```cpp
auto root = (h - sqrtd) / a;                        // near root
if (root <= ray_tmin || ray_tmax <= root) {
    root = (h + sqrtd) / a;                         // try far root
    if (root <= ray_tmin || ray_tmax <= root)
        return false;
}
```

Cases where the **far** root is the answer:
- camera inside the sphere (near root negative)
- ray starting on a surface after a bounce (near root ≈ 0, rejected by `tmin`)
- both negative → object behind camera → correctly no hit

**Historical bug (now fixed):** testing only `discriminant >= 0` tests the infinite **line**, which extends backwards through the camera. A sphere at (0,0,+1) — behind the camera — still rendered. Solving for `t` and rejecting non-positive values fixes it.

### Normals

```cpp
vec3 outward_normal = (rec.p - center) / radius;
```

Divides by radius rather than calling `unit_vector` — the centre-to-surface distance **is** the radius by definition, so no `sqrt` needed. Requires positive radius, hence the `std::fmax(0, radius)` clamp in the constructor.

---

## 9. Front faces

Needed for objects with an inside and an outside (glass). A ray can hit a surface from either side.

**Convention chosen:** normals always point **against the incoming ray**, with the side stored separately. Decided at geometry time rather than shading time because there are more material types than geometry types — fewer places to write the check.

```cpp
front_face = dot(r.direction(), outward_normal) < 0;
normal = front_face ? outward_normal : -outward_normal;
```

The sign of a dot product is the sign of `cos θ`:

| situation | ray vs outward normal | dot | front_face |
|---|---|---|---|
| hitting the outside | oppose (going in vs coming out) | negative | `true` |
| hitting from inside | agree (both heading outward) | positive | `false` |

`set_face_normal` **assumes unit length** — it does not normalise. Each geometry type knows its own cheap shortcut, so normalisation belongs in the geometry code.

---

## 10. The hittable design

### `hit_record`

Plain data holder: `p`, `normal`, `t`, `front_face`. Uninitialised until `hit` writes to it — fine, since it's only read when `hit` returned `true`.

The design decision: compute **everything** on every hit and discard most of it, rather than deferring normal computation until the closest object is known. Simpler; wasted work is a few multiplications. Production renderers often defer instead.

### `hittable` — abstract base

```cpp
virtual ~hittable() = default;
virtual bool hit(const ray& r, interval ray_t, hit_record& rec) const = 0;
```

| syntax | meaning |
|---|---|
| `virtual` | dispatch decided at **runtime** from the actual object, not the declared type. The whole design depends on this |
| `= 0` | **pure virtual** — no implementation. Makes the class abstract (can't instantiate). Derived classes *must* implement it |
| `virtual ~hittable()` | needed because objects are deleted through base pointers. Without it, `~sphere()` never runs. Any class meant to be inherited from gets one |
| `hit_record& rec` | **output parameter** — non-const reference, the function writes into it. Returns `bool` for "hit?", fills `rec` with "where" |

### `sphere : public hittable`

```cpp
sphere(const point3& center, double radius)
    : center(center), radius(std::fmax(0, radius)) {}
```

Parameter and member share a name — unambiguous **in the initialiser list** (outside the parens = member, inside = parameter). Would be ambiguous in the constructor body.

`override` is optional but always worth writing: it makes the compiler verify a matching virtual function exists. A signature mismatch (e.g. forgetting the trailing `const`) silently creates a *new* function instead of overriding, leaving the class abstract with a confusing error far from the mistake.

### `hittable_list : public hittable`

A hittable that holds hittables — the composite pattern. Lists can nest inside lists (this is how BVHs get built later).

```cpp
std::vector<shared_ptr<hittable>> objects;
```

Can't store `hittable` by value: it's abstract, and storing a `sphere` in a `hittable` slot would slice off the derived part. **Polymorphism requires indirection.**

`shared_ptr` = pointer + reference count; auto-deletes at zero. This is why `hittable` needed the virtual destructor.

### The closest-hit loop

```cpp
auto closest_so_far = ray_tmax;
for (const auto& object : objects) {
    if (object->hit(r, interval(ray_tmin, closest_so_far), temp_rec)) {
        hit_anything = true;
        closest_so_far = temp_rec.t;   // shrink the search window
        rec = temp_rec;
    }
}
```

**There is no distance comparison.** No `if (t < best_t)`. Each hit shrinks `tmax`, so subsequent objects are only asked about *nearer* intersections and reject themselves before computing normals. The interval parameter **is** the comparison.

`const auto&` deduces `const shared_ptr<hittable>&` — reference avoids touching the reference count. `object->hit` uses `->` because it's a pointer, and this is where virtual dispatch happens.

---

## 11. The `camera` class

**Public = knobs, private = derived state.**

```cpp
public:
    double aspect_ratio = 1.0;      // default member initialisers
    int    image_width = 100;
    int    samples_per_pixel = 10;
```

No constructor. Named assignment reads better than positional arguments when there are several settings, and new settings can be added without breaking existing code.

Cost of that choice: derived values can't be computed at construction (the settings aren't known yet), so `initialize()` runs at the top of `render()`.

Only promote to a member what needs to survive. `focal_length`, `viewport_height`, `viewport_upper_left` stay as `auto` locals inside `initialize()`.

---

## 12. Antialiasing and Monte Carlo

### The problem

One ray per pixel through the exact centre → a pixel is either fully object or fully background. Silhouettes come out as stair-steps. That's **aliasing**: sampling too sparsely to represent the signal.

### The fix

```cpp
color pixel_color(0, 0, 0);
for (int sample = 0; sample < samples_per_pixel; sample++) {
    ray r = get_ray(i, j);
    pixel_color += ray_color(r, world);
}
write_color(std::cout, pixel_samples_scale * pixel_color);
```

Several rays per pixel at **random positions within the pixel square**, averaged. A pixel straddling an edge gets some object samples and some background samples; the average is a blend.

```cpp
vec3 sample_square() const {
    return vec3(random_double() - 0.5, random_double() - 0.5, 0);
}

auto pixel_sample = pixel00_loc
    + ((i + offset.x()) * pixel_delta_u)
    + ((j + offset.y()) * pixel_delta_v);
```

`i + offset.x()` is a **fractional** pixel index. Offset range ±0.5 with a step of one delta means samples cover exactly the pixel's square and never spill into a neighbour.

`pixel_samples_scale = 1.0 / samples_per_pixel` is computed once in `initialize()` — multiplication is cheaper than division, and this runs per pixel.

### Why random rather than a regular grid

A fixed 3×3 grid also reduces aliasing but introduces its own **structured** artifact. Random sampling converts structured error into **noise**, which the eye tolerates far better and which averages away. Trading aliasing for noise is one of the foundational trades in rendering.

### This is Monte Carlo integration

The average colour over a pixel's area is an **integral** with no closed form. Estimate it by random sampling.

> **Error falls as 1/√N.** 4× the samples → half the noise. 16× → a quarter.

**Observed:** 100 → 400 samples gave a visible improvement; 400 → 1600 looked identical. Both steps are 4× and both halve the error — but the *absolute* reduction shrinks each time (1.0 → 0.5 removes 0.5; 0.5 → 0.25 removes only 0.25). Below ~1/255 per channel the residual quantises away in `write_color` entirely.

Also: with the current deterministic `ray_color`, the **only** randomness is sub-pixel position. Interior pixels return the same colour every sample. All the work happens on a thin band of silhouette pixels, which converge fast. Once diffuse materials add random bounce directions, the whole frame becomes a noisy estimate and higher sample counts matter across the board.

**Why this matters beyond antialiasing:** 1/√N is the reason importance sampling exists. If brute force only buys you 1/√N, the way to a clean image is to make each sample count more — put samples where they matter. That is exactly what many-lights sampling (Gadia) and neural importance sampling (Kalantari) do. Right now the integral is 2D (position in a pixel); every bounce adds dimensions, but the machinery is unchanged.

---

## 13. C++ mechanics reference

### `const` — three positions, three jobs

```cpp
double operator[](int i) const { return e[i]; }
//     ^^ return type            ^^^^^ trailing
```

| position | meaning |
|---|---|
| `const vec3& v` (parameter) | won't modify the **argument** |
| `double f() const` (trailing) | won't modify the **object**. Member functions only |
| `const point3& origin()` (return) | the returned reference is read-only — stops callers writing into a private member |

**Rule:** mark every member function `const` unless it needs to modify. Otherwise it can't be called on a `const vec3&`, which is how everything is passed.

### `&` and `*` — two meanings each

| where | meaning |
|---|---|
| `vec3& r` (declaration) | **reference** — an alias, no copy, can't be rebound |
| `&a` (expression) | address-of |
| `vec3* p` (declaration) | **pointer** — holds an address |
| `*p` (expression) | the object pointed at |
| `*this` (in a member function) | the current object itself |

Parameter passing:

```cpp
void f(vec3 v);          // copies 24 bytes
void f(vec3& v);         // no copy, CAN modify caller's object
void f(const vec3& v);   // no copy, CANNOT modify  ← the default choice
```

`return *this;` with return type `vec3&` hands back the object itself, not a copy — that's what makes `(a += b) += c` work.

### Other syntax

| syntax | meaning |
|---|---|
| `auto` | deduce type from initialiser. Deduces the **value** type — strips references unless you write `auto&` |
| `: e{0,0,0}` | member initialiser list — runs *before* the body, initialises directly rather than default-then-assign |
| `cond ? a : b` | ternary — an **expression**, produces a value |
| `#ifndef X / #define X / #endif` | include guard; same job as `#pragma once` |
| `#include "..."` vs `<...>` | quotes = project files (search locally first); angles = standard library |
| `inline` (free function in a header) | tells the linker duplicate definitions across translation units are expected |

---

## 14. Gotchas hit so far

**Integer division.** `i / (image_width - 1)` with both `int` truncates to 0 for every column except the last → black image with one red stripe. C++ picks the division based on **operand types**, before values are involved, and gives no warning.

```cpp
double(i) / (image_width - 1)     // correct — cast an OPERAND
double(i / (image_width - 1))     // WRONG — division already happened as ints
```

**PowerShell redirection.** `>` writes UTF-16 → BOM and null bytes → IrfanView rejects the file. Use cmd, or `cmd /c "... > image.ppm"`.

**Progress output.** Must go to `std::clog` or `std::cerr`. `std::cout` is redirected into the PPM and would corrupt it.

**Exe location.** For x64 builds Visual Studio puts the binary in the **solution** folder (`..\x64\Debug\`), not the project folder. Both folders share the same name.

**Header include hygiene.** Currently compiles only by accident of include order. See §2.

---

## 15. Where this is going

**Next:** diffuse materials — random bounce directions, recursion, `interval(0.001, infinity)` to fix shadow acne from rays re-hitting their own surface at t ≈ 1e-15.

**Then:** metal (reflection), dielectrics (refraction, uses `front_face`), positionable camera, defocus blur.

**Planned experiment — convergence study.** Render the same scene at 1, 4, 16, 64, 256 spp. Compute MSE against a 1024-spp reference. Plot error vs sample count on log-log axes; expect a slope near −1/2.

Run this **after** diffuse materials are in — the current scene has too little variance for the curve to be visible.

**Planned extension — many lights.** Add emissive materials and dozens of lights; compare uniform vs intensity-weighted light selection at equal sample counts. This is the offline-rendering counterpart to the real-time many-lights problem, and the bridge to neural importance sampling.
