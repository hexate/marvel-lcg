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
            // v2 draws at 1:1, so scene coordinates are already screen pixels. `hover.ts` scales by
            // this to place the card preview, and the initial 0 silently collapsed those to the
            // scene's origin. There is no transform to divide out, so the factor is 1.
            Scene.scale = 1
            document.getElementById('camera')!.style.display = 'unset'
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

// Function to convert scene position to window position
export function convertScenePosToWindowPos(sceneX: number, sceneY: number) {
    const scene = document.getElementById('scene')!;
    const rect = scene.getBoundingClientRect(); // Get the bounding rectangle of the scene

    // Get the current scale of the scene
    const scale = Scene.scale; // Assuming Scene.scale holds the current scale value

    // Calculate the window position
    const windowX = (sceneX * scale) + rect.left; // Adjusted X position in window coordinates
    const windowY = (sceneY * scale) + rect.top;  // Adjusted Y position in window coordinates

    return { x: windowX, y: windowY };
}

// Function to get mouse position relative to the scene
export function getMousePositionInScene(windowX: number, windowY: number) {
    const scene = document.getElementById('scene')!;
    const rect = scene.getBoundingClientRect(); // Get the bounding rectangle of the scene

    // Calculate the mouse position relative to the scene
    const mouseX = windowX - rect.left; // Mouse X relative to the scene
    const mouseY = windowY - rect.top;  // Mouse Y relative to the scene

    // Adjust for scaling
    const scale = Scene.scale; // Extract the scale value
    const sceneX = mouseX / scale; // Adjusted X position
    const sceneY = mouseY / scale; // Adjusted Y position

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

