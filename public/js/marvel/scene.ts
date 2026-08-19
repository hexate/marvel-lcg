import { Lib } from './lib.js'
import { Setting } from "./settings.js";
import { HoverCard } from './hover.js';

export class Scene {
    static scale: number = 0

    /** Whether the rebuilt layout is in charge.
     *
     *  Read from the page, not the URL. The server decides which page to send; if this asked the
     *  URL instead it would be a second, independent opinion, and the two can disagree. They did:
     *  a cached v1 page opened at a v2 URL had this return true, so the guard below skipped v1's
     *  scaling on a page that needs it, and the board rendered unscaled and half off screen.
     *
     *  The page that was actually served is the only thing that knows the answer. */
    static isV2(): boolean {
        return document.body?.dataset.layout === 'v2'
    }

    static init() {
        // v2 lets CSS own the scale, so none of this may run: the transform and the inline
        // left/top below would fight the container-query layout and win, because inline styles
        // beat stylesheets. See `public/js/marvel2/layout.ts`.
        if (Scene.isV2()) {
            // There is no camera transform under v2, so the factor is 1. Note what that does and
            // does not mean: it does NOT mean a scene coordinate is a screen pixel, which is what
            // this comment used to claim. v2 keeps the coordinates and changes the unit to a
            // fraction of the container, `--sux` across and `--su` down. Anything converting a
            // coordinate needs the unit as well as this scale; see `convertScenePosToWindowPos`,
            // and `Lib.client.sceneUnit()` for the unit. Reading this as "already pixels" produced
            // three separate defects, J19, J22 and J23. The initial 0 mattered too: it silently
            // collapsed the preview position to the scene's origin.
            Scene.scale = 1
            document.getElementById('camera')!.style.display = 'unset'

            // The preview panels still have to be measured, even though v2 has no scale to
            // compute. `HoverCard.onMouseMove` chooses which side to show a card preview on by
            // testing the hovered card against `rect_left` and `rect_right`, and the only thing
            // that ever refreshed those was `adjustSceneScale`, which is exactly what this branch
            // skips. The class initialiser measures once at module load, before the panels are
            // laid out, so on their own they stay at zero, and a zero-size rect at the origin can
            // never overlap: the preview would sit on one side whatever card was hovered.
            //
            // The panels live outside `#camera` and are sized in `vh`, so there is no unit to
            // convert here. They only need measuring once the layout exists, and again whenever
            // the window changes it.
            //
            // Registered unconditionally, the way the v1 branch below does it, and deliberately
            // not behind a `readyState === 'loading'` check. This module is loaded with
            // `type="module"`, which defers, so it executes at readyState `'interactive'`: such a
            // check takes its else branch and measures immediately, which is still too early and
            // reads zeros. A listener added during `'interactive'` has not missed the event.
            // `'complete'` is the one case where it has, which only arises on a late dynamic
            // import, so that measures on the spot instead.
            //
            // `addEventListener` rather than `window.onresize =`, which is what the v1 branch
            // uses, so this cannot quietly replace another handler.
            if (document.readyState === 'complete') {
                HoverCard.updateRect()
            }
            document.addEventListener('DOMContentLoaded', () => HoverCard.updateRect())
            window.addEventListener('resize', () => HoverCard.updateRect())
            return
        }

        // Adjust scale on DOMContentLoaded
        document.addEventListener('DOMContentLoaded', () => {
            adjustSceneScale()
        });

        // Adjust scale on resize
        window.onresize = () => {
            adjustSceneScale();
        }

        // import { HoverCard } from "./hover.js";
        if( Setting.scene_3d ) {
            Lib.loader.loadCSS("./css./marvel./scene-3d.css")
            document.body.classList.add('scene-3d')
        }
    }
}

/** Where a scene coordinate lands in the window.
 *
 * Two things stand between a scene coordinate and a window pixel, and only one of them is
 * `Scene.scale`.
 *
 * The unit comes first: a scene coordinate is a position on the 1920x1080 canvas the board was
 * authored against. v1 lays one unit out as `1px`, v2 as a fraction of the container, `--sux`
 * across and `--su` down. Then the transform: v1 scales the whole camera by `Scene.scale`, v2 has
 * no transform and leaves it at 1. So each layout contributes on a different one of the two and
 * both terms are needed, which is why this used to look right with only the second. Under v1 the
 * unit is 1 and this is arithmetically the line it replaces.
 *
 * The comment in `init` used to say v2 draws at 1:1, so scene coordinates are already screen
 * pixels. The 1 is right, in the narrow sense that there is no transform to divide out. The
 * reason was not, and it is the belief behind J19, J22 and J23.
 */
export function convertScenePosToWindowPos(sceneX: number, sceneY: number) {
    const scene = document.getElementById('scene')!;
    const rect = scene.getBoundingClientRect(); // Get the bounding rectangle of the scene

    const scale = Scene.scale;
    const unit = Lib.client.sceneUnit();

    const windowX = (sceneX * unit.x * scale) + rect.left;
    const windowY = (sceneY * unit.y * scale) + rect.top;

    return { x: windowX, y: windowY };
}

// Function to get mouse position relative to the scene
export function getMousePositionInScene(windowX: number, windowY: number) {
    const scene = document.getElementById('scene')!;
    const rect = scene.getBoundingClientRect(); // Get the bounding rectangle of the scene

    // Calculate the mouse position relative to the scene
    const mouseX = windowX - rect.left; // Mouse X relative to the scene
    const mouseY = windowY - rect.top;  // Mouse Y relative to the scene

    // Adjust for scaling. The exact inverse of `convertScenePosToWindowPos`, so it divides out
    // both terms for the same reason that one multiplies by both. Nothing calls this today, and it
    // is corrected rather than left because an inverse that disagrees with its forward function is
    // a trap for whoever calls it first.
    const scale = Scene.scale;
    const unit = Lib.client.sceneUnit();
    const sceneX = mouseX / (unit.x * scale);
    const sceneY = mouseY / (unit.y * scale);

    return { x: sceneX, y: sceneY };
}

export function adjustSceneScale() {
    const camera = document.getElementById('camera')!;
    const rootStyles = getComputedStyle(document.documentElement); // Get the root element's styles

    // Read the width and height from CSS variables
    const sceneWidth = parseFloat(rootStyles.getPropertyValue('--scene-width'));
    const sceneHeight = parseFloat(rootStyles.getPropertyValue('--scene-height'));

    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    // Calculate scale factors
    const scaleX = viewportWidth / sceneWidth;
    const scaleY = viewportHeight / sceneHeight;
    Scene.scale = Math.min(scaleX, scaleY); // Use the smaller scale to fit within the viewport

    // Apply the scale transformation
    camera.style.transform = `scale(${Scene.scale})`;
    if( Setting.scene_3d ) {
        document.getElementById('scene')!.style.transform = `scale(1) rotateX(20deg)`;
    }
    camera.style.display = "unset";

    // Center the scene in the viewport
    camera.style.left = `${(viewportWidth - (sceneWidth * Scene.scale)) / 2}px`;
    camera.style.top = `${(viewportHeight - (sceneHeight * Scene.scale)) / 2}px`;

    // Set the new value for the CSS variable
    // Must use `parseInt`
    const x = parseInt(rootStyles.getPropertyValue('--font-size'));
    document.documentElement.style.setProperty('--font-size-out', `${x * Scene.scale}px`);

    HoverCard.updateRect()
}

