# Loading animation feasibility — stock Batocera 42

Source inspected via pinned Git objects at `/tmp/ra-es-source`, ES revision `4adf26b43900d1a33887af6d8af3da2e99e398a5`.

User approved three sequential pulsing dots under Eudora artwork, with stationary game logo and palette-aware colour. This supersedes the earlier no-activity-graphics design, but does not authorize a custom frontend or external launch hook.

## Blocker

`es-core/src/Splash.cpp` constructs standalone extras with `ThemeData::makeExtras`, binds them once, and renders them. Its `update(std::string,float)` only changes label/progress. It does not call extra-component `update(deltaTime)`. `GuiComponent.cpp:65–98` advances storyboard animations only through that update path. Image playlists likewise require `ImageComponent::update` (1013–1031). Therefore adding ordinary theme storyboards/image playlists here does not provide a running dot animation.

Video is a recognized extra (`ThemeData.cpp:2202–2203`) but is not a verified workaround: `VideoComponent.cpp:204–206` suppresses video start handling while `isLaunchTransitionRunning`. `ViewController.cpp:567` sets that flag during game launch. `VideoVlcComponent.cpp:434–444` also suppresses a zero-fade frame, and normal update progression is missing for splash extras.

`Window.cpp:935–960` constructs Splash and invokes render; no animation-update hook is provided there. Splash resets extras' opacity each render, another obstacle to directly animating component alpha.

## Outcome

No ineffective runtime XML, fabricated animation support, frontend patch, or launch hook installed. Existing Eudora candidate retained unchanged. A normal dot storyboard requires frontend lifecycle changes and verification; an external loading window is a separate solution with handoff/timing risks, not a theme-only addition. This is source-level feasibility evidence, not a native GUI runtime test. No broad claim is made about every possible shader or custom renderer workaround.
