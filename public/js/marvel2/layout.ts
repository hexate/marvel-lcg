// @ts-check
"use strict";

/**
 * v2 layout support.
 *
 * Deliberately small. The geometry is CSS now (`public/css/marvel2/layout.css`), so there is no
 * scale to compute, nothing to recompute on resize, and no measure-then-apply cycle to go stale.
 * What is left is the things a second layout genuinely needs: a way to switch back, and a way to
 * see what the layout is doing while it is being worked on.
 */

/** The opt-out flag. v2 is what you get by default; this asks for the original layout back. */
const V1_FLAG = 'v1'

/** Accepted but redundant, so that links written while v2 was opt-in still land on v2. */
const V2_FLAG = 'v2'

export class Layout2 {

    /** Must match `handle_marvel` on the server and `Scene.isV2`, or the page and the script
     *  disagree about which layout is on screen. */
    static isActive(): boolean {
        return !new URLSearchParams(location.search).has(V1_FLAG)
    }

    /** The same board URL with the layout flipped, so switching keeps the game and the seat. */
    static otherVersionUrl(): string {
        const url = new URL(location.href)
        if (Layout2.isActive()) {
            // Going back to v1. Drop the now-redundant v2 flag so the URL says one thing.
            url.searchParams.delete(V2_FLAG)
            // Valueless, to match how the other board flags in this query string are written.
            url.search = url.search ? `${url.search}&${V1_FLAG}` : `?${V1_FLAG}`
        } else {
            url.searchParams.delete(V1_FLAG)
            // v2 is the default, so removing the opt-out is enough. Guard against an empty query
            // string, which the server reads as "show the menu" rather than "show the board".
            if (!url.search || url.search === '?') url.search = `?${V2_FLAG}`
        }
        return url.toString()
    }

    /**
     * Live layout metrics.
     *
     * Reported rather than used: the point of v2 is that nothing here feeds back into the layout.
     * It is for answering "what size does the board think it is" without opening devtools.
     */
    static metrics() {
        const scene = document.getElementById('scene')
        const cs = scene ? getComputedStyle(scene) : null
        const cardH = cs ? parseFloat(cs.getPropertyValue('--card-height')) : 0
        const rows = cs ? parseFloat(cs.getPropertyValue('--scene-rows')) : 1080
        return {
            version: Layout2.isActive() ? 'v2' : 'v1',
            viewport: `${window.innerWidth}x${window.innerHeight}`,
            cardHeight: Math.round(cardH * 10) / 10,
            // What the board would have been on the fixed 16:9 canvas, for comparison.
            v1UsableWidth: Math.round(1920 * Math.min(window.innerWidth / 1920, window.innerHeight / rows)),
            usableWidth: window.innerWidth,
        }
    }

    /**
     * A corner control to switch layouts.
     *
     * Two versions are only worth having if flipping between them is one click, otherwise nobody
     * compares them and the old one quietly rots.
     */
    static addSwitch(): void {
        const link = document.createElement('a')
        link.id = 'layout-version-switch'
        link.href = Layout2.otherVersionUrl()
        link.textContent = Layout2.isActive() ? 'v2' : 'v1'
        link.title = Layout2.isActive()
            ? 'Layout v2. Click for the original.'
            : 'Original layout. Click for v2.'
        document.body.appendChild(link)

        // Hovering reports what the layout is doing, which is the question being asked most while
        // this is in flight.
        link.addEventListener('mouseenter', () => {
            const m = Layout2.metrics()
            link.title = `${m.version}  ${m.viewport}\n`
                + `card ${m.cardHeight}px\n`
                + `board width ${m.usableWidth}px (v1 would be ${m.v1UsableWidth}px)`
        })
    }
}

// The v1 client builds the board, so wait for it rather than racing it.
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => Layout2.addSwitch())
} else {
    Layout2.addSwitch()
}

// Handy from the console while comparing the two.
;(window as any).Layout2 = Layout2
