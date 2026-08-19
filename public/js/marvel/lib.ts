export { };

declare global {
    interface Array<T> {
        /**
         * Pushes `item` if not already included.
         * @returns true if pushed, false if skipped.
         */
        pushUnique(item: T): boolean;
    }
}

if (!Array.prototype.pushUnique) {
    Array.prototype.pushUnique = function <T>(this: T[], item: T): boolean {
        if (!this.includes(item)) {
            this.push(item);
            return true;
        }
        return false;
    };
}

declare global {
    interface Set<T> {
        /**
         * If `value` is in the set, remove it and return false.
         * Otherwise add it and return true.
         */
        toggle(value: T): boolean;
    }
}

if (!Set.prototype.toggle) {
    Set.prototype.toggle = function <T>(this: Set<T>, value: T): boolean {
        if (this.has(value)) {
            this.delete(value);
            return false;
        } else {
            this.add(value);
            return true;
        }
    };
}

class Cookie {

    // Function to set a cookie
    static set(name: string, value: string, days: number = 36500): void {
        const expires = new Date(Date.now() + days * 864e5).toUTCString();
        document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/`;
    }

    static get(name: string): string | null {
        const nameEQ = `${name}=`;
        const ca = document.cookie.split(';');
        for (let i = 0; i < ca.length; i++) {
            let c = ca[i].trim(); // Trim whitespace
            if (c.indexOf(nameEQ) === 0) return decodeURIComponent(c.substring(nameEQ.length, c.length)); // Return the cookie value
        }
        return null;
    }

    private static setJSON(name: string, data: any, days?: number) {
        Cookie.set(name, JSON.stringify(data), days);
    }

    private static getJSON<T>(name: string): T | null {
        const raw = Cookie.get(name);
        if (!raw) return null;
        try { return JSON.parse(raw); } catch { return null; }
    }

    static setList(name: "debug_inputs" | "auto_activate_faces", value: string[]): void {
        Cookie.setJSON(name, value);
    }

    static getList(name: "debug_inputs"): string[] {
        return Cookie.getJSON<string[]>(name) ?? [];
    }

    static getSet(name: "auto_activate_faces" | "render_card_blacklist" | "render_card_whitelist" | "render_under_card_whitelist", default_value: string[] = []): Set<string> {
        const arr = this.getJSON<string[]>(name);
        return new Set(Array.isArray(arr) && arr.length > 0 ? arr : default_value);
    }

    static setSet(name: "render_card_blacklist" | "render_card_whitelist" | "render_under_card_whitelist", data: Set<string>, days?: number): void {
        this.setJSON(name, Array.from(data), days);
    }

    static setString(name: "app_version", value: string): void {
        Cookie.set(name, value);
    }

    static getString(name: "app_version"): string {
        return Cookie.get(name) ?? "";
    }

    static setBool(name: string, value: boolean) {
        Cookie.set(name, value ? '1' : '0');
    }

    static getBool(name: string): boolean {
        return Cookie.get(name) === '1';
    }

    static getBtnString(name: string): string {
        return Cookie.get(name) ?? "";
    }
    static setBtnString(name: string, value: string) {
        Cookie.set(name, value);
    }
}

class MyArray {
    // Deep-clone a nested array
    static deepClone(arr: any[]): any[] {
        return arr.map(item =>
            Array.isArray(item)
                ? MyArray.deepClone(item)
                : item
        );
    }

    // Count how many times `value` appears
    static occurrence<T>(arr: T[], value: T): number {
        return arr.filter(v => v === value).length;
    }

    // True if there’s any duplicate
    static hasDuplicates<T>(arr: T[]): boolean {
        return new Set(arr).size !== arr.length;
    }

    // True if two arrays are strictly equal, element by element
    static equals<T>(a: T[], b: T[]): boolean {
        return (
            a.length === b.length &&
            a.every((v, i) => v === b[i])
        );
    }
}


class MyObject {
    static deepCopy<T>(obj: T): T {
        if (obj === null || typeof obj !== 'object') {
            return obj;
        }
        if (Array.isArray(obj)) {
            return obj.map(item => MyObject.deepCopy(item)) as unknown as T;
        }
        const copy = {} as { [key: string]: any };
        for (const key in obj) {
            if (Object.prototype.hasOwnProperty.call(obj, key)) {
                copy[key] = MyObject.deepCopy((obj as any)[key]);
            }
        }
        return copy as T;
    }

    static isEmpty(obj: object = {}): boolean {
        return Object.keys(obj).length === 0;
    }

    static objectsEqual(
        a: Record<string, any>,
        b: Record<string, any>
    ): boolean {
        const ka = Object.keys(a),
            kb = Object.keys(b);
        if (ka.length !== kb.length) return false;
        return ka.every(k => a[k] === b[k]);
    }

    static hashObjectFast(obj: any): string {
        const FNV_PRIME = 0x01000193;
        let hash = 0x811c9dc5; // FNV offset basis

        function mixBytes(bytes: Uint8Array) {
            for (let b of bytes) {
                hash ^= b;
                hash = Math.imul(hash, FNV_PRIME) >>> 0;
            }
        }

        function walk(value: any) {
            if (value === null) {
                mixBytes(new Uint8Array([0x00]));
            }
            else if (typeof value === "boolean") {
                mixBytes(new Uint8Array([value ? 0x01 : 0x02]));
            }
            else if (typeof value === "number") {
                // 64-bit float → 8 bytes
                const buf = new ArrayBuffer(8);
                new DataView(buf).setFloat64(0, value, true);
                mixBytes(new Uint8Array(buf));
            }
            else if (typeof value === "string") {
                mixBytes(new TextEncoder().encode(value));
                mixBytes(new Uint8Array([0x00])); // separator
            }
            else if (Array.isArray(value)) {
                mixBytes(new Uint8Array([0xF0]));
                for (let el of value) walk(el);
                mixBytes(new Uint8Array([0xF1]));
            }
            else if (typeof value === "object") {
                mixBytes(new Uint8Array([0xE0]));
                // sort keys once per object
                const keys = Object.keys(value).sort();
                for (let key of keys) {
                    mixBytes(new TextEncoder().encode(key));
                    mixBytes(new Uint8Array([0x00]));
                    walk(value[key]);
                }
                mixBytes(new Uint8Array([0xE1]));
            }
            else {
                // functions, symbols, undefined
                mixBytes(new Uint8Array([0xFF]));
            }
        }

        walk(obj);

        // return as unsigned 32-bit hex or decimal
        // hex is shorter:
        return hash.toString(16);
    }

}

class Loader {
    /**
     * Load a JavaScript file and return a promise.
     * Strips ".js" suffix if present and the URL isn’t absolute.
     */
    static loadJSAsync(src: string): Promise<void> {
        if (!src.endsWith('.js')) {
            throw new Error(`Not a JS file: ${src}`);
        }
        if (!/^https?:\/\//i.test(src)) {
            src = src.slice(0, -3);
        }

        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.type = 'text/javascript';
            script.src = src;
            script.onload = () => resolve();
            script.onerror = () => reject(new Error(`Failed to load ${src}`));
            document.head.appendChild(script);
        });
    }

    static loadJS(src: string, callback?: () => void): void {
        if (!src.endsWith('.js')) {
            throw new Error(`Not a JS file: ${src}`);
        }
        src = src.slice(0, -3);
        const script = document.createElement('script');
        script.type = 'text/javascript';
        script.src = src;
        script.onload = () => callback?.();
        document.head.appendChild(script);
    }

    static loadCSS(href: string): void {
        if (!href.endsWith('.css')) {
            throw new Error(`Not a CSS file: ${href}`);
        }
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.type = 'text/css';
        link.href = href;
        document.head.appendChild(link);
    }

    /**
     * Load either a JS or CSS file.
     * Returns a promise if JS, void otherwise.
     */
    static loadFile(
        filename: string,
        callback?: () => void
    ): void | Promise<void> {
        if (filename.endsWith('.js')) {
            return callback
                ? Loader.loadJS(filename, callback)
                : Loader.loadJSAsync(filename);
        } else if (filename.endsWith('.css')) {
            Loader.loadCSS(filename);
        } else {
            throw new Error(`Unsupported file type: ${filename}`);
        }
    }
}

class Client {

    static getOffsetClient(el: HTMLElement): { left: number; top: number; right: number; bottom: number; width: number; height: number } {
        if (el == null) {
            Lib.alert()
        }
        const rect = el.getBoundingClientRect();
        const scrollX = window.scrollX; // Cache scroll values
        const scrollY = window.scrollY;
        return {
            left: rect.left + scrollX,
            top: rect.top + scrollY,
            right: rect.right + scrollX,
            bottom: rect.bottom + scrollY,
            width: rect.width,
            height: rect.height,
        };
    }

    /**
     * Gets the offset of an HTML element.
     */
    static getOffset(el: HTMLElement): { left: number; top: number; } {
        let x = el.style.getPropertyValue('--x')
        if (x) {
            let y = el.style.getPropertyValue('--y')
            let tx = Number(x)
            let ty = Number(y)
            // let w = el.offsetWidth
            // let h = el.offsetHeight
            return {
                left: tx,
                top: ty,
                // right: tx + w,
                // bottom: ty + h,
                // width: w,
                // height: h,
            };
        }
        else {
            return {
                left: 0,
                top: 0
            }
        }
    }

    /** One scene unit, in real pixels, on each axis.
     *
     * `getOffset` returns scene coordinates: positions on the 1920x1080 canvas the board was
     * authored against, not pixels. v1 makes one unit `1px` and scales the whole camera, so both
     * come back 1 and any caller that treated them as pixels was accidentally right. v2 keeps the
     * coordinates and makes a unit a fraction of the container, `--sux` across and `--su` down, so
     * they differ from each other and from 1, and such a caller is wrong by the difference.
     *
     * Measured off a probe rather than computed, so neither the canvas size nor the unit formula
     * is repeated here and `layout.css` stays the only place that knows them. `getComputedStyle`
     * rather than `getBoundingClientRect`, because the used width ignores v1's camera transform
     * and a rect does not. `getComputedStyle` rather than `offsetWidth`, because that rounds to an
     * integer and the fraction is the whole point. A thousand units keeps the reading well clear
     * of any rounding, and the `1px` fallbacks are what make v1, which defines neither variable,
     * measure exactly 1000.
     */
    static sceneUnit(): { x: number; y: number } {
        const scene = document.querySelector('#scene')!
        const probe = document.createElement('div')
        probe.style.position = 'absolute'
        probe.style.visibility = 'hidden'
        probe.style.pointerEvents = 'none'
        probe.style.width = 'calc(1000 * var(--sux, 1px))'
        probe.style.height = 'calc(1000 * var(--su, 1px))'
        scene.appendChild(probe)
        const style = getComputedStyle(probe)
        const unit = {
            x: parseFloat(style.width) / 1000,
            y: parseFloat(style.height) / 1000,
        }
        probe.remove()
        return unit
    }

    static getOffset2(elx: HTMLElement) {

        return Client.getOffset(elx)
        // return Lib.getOffset(elx)
        // let x = 0;
        // let y = 0;

        // let el = elx.offsetParent as HTMLElement | null;
        // // Get the element's position relative to the document
        // while (el) {
        //     x += el.offsetLeft;
        //     y += el.offsetTop;
        //     el = el.offsetParent as HTMLElement | null;
        // }

        // // Get the dimensions of the element
        // const width = elx.offsetWidth;
        // const height = elx.offsetHeight;

        // return {
        //     left: x,
        //     top: y,
        //     right: x + width,
        //     bottom: y + height,
        //     width: width,
        //     height: height,
        // };
    }
}

class MyString {
    /**
     * Checks if a string is numeric.
     */
    static isNumeric(str: string): boolean {
        return !isNaN(parseFloat(str));
    }

    /**
     * Inserts hyphens before uppercase characters in a string and converts it to lowercase.
     */
    static insertHyphens(input: string): string {
        return input.split('').map((char, index) => {
            if (char === char.toUpperCase() && index !== 0) {
                return '-' + char;
            }
            return char;
        }).join('').toLocaleLowerCase();
    }

    static isStringANumber(value: string): boolean {
        return !isNaN(parseFloat(value)) && isFinite(Number(value));
    }
}

class Game {

    static removeTypeClasses(divElement: HTMLElement): void {
        // Get the div element by its ID
        if (divElement) {
            // Get the current class list
            const classList: DOMTokenList = divElement.classList;

            // Create an array to hold classes to remove
            const classesToRemove: string[] = [];

            // Iterate through the class list
            classList.forEach((className: string) => {
                // Check if the class name starts with "type_"
                if (className.startsWith('type-')) {
                    classesToRemove.push(className);
                }
            });

            // Remove the classes that start with "type_"
            classesToRemove.forEach((className: string) => {
                divElement.classList.remove(className);
            });
        }
    }

    static addTypeClass(divElement: HTMLElement, class_name: string, name: string=""): void {
        divElement.classList.add(`type-${Lib.string.insertHyphens(class_name)}`)
        if( name && class_name == "StatusCard" ) {
            divElement.classList.add(`type-${Lib.string.insertHyphens(class_name + name)}`)
        }
    }

    static cleanResText(input: string): string {
        const cardTypes = ["mental", "physical", "energy", "wild", 'boost'];
        cardTypes.forEach(c => {
            input = input.replaceAll(`[[${c}]]`, `<span class='icon-${c}'></span>`);
            input = input.replaceAll(`[${c}]`, `<span class='icon-${c}'></span>`);
        });
        return input;
    }
}

export class Lib {

    static cookie = Cookie
    static array = MyArray
    static object = MyObject

    static loader = Loader
    static client = Client
    static string = MyString

    static game = Game

    static getCallerFunctionName(level: number = 1): string {
        function getErrorObject(): Error {
            return new Error('');
        }

        try {
            const err: Error = getErrorObject();
            const callerLine: string = err.stack?.split("\n")[3 + level] || "";
            const index: number = callerLine.indexOf("at ");
            const match = callerLine.match(/at ([\w\.]+)/);
            const callerName: string = match ? match[1] : "";
            return callerName;
        } catch (error) {
            return "";
        }
    }

    static assert(condition: boolean, message: any = null): void {
        if (!condition) {
            throw new Error(message);
        }
    }

    static alert(text = '') {
        function getErrorObject(): Error {
            return new Error('');
        }

        const err = getErrorObject();
        const caller_line = err.stack?.split("\n")[4];
        var index = caller_line?.indexOf("at ") ?? 0;
        var clean = caller_line?.slice(index + 2, caller_line.length);

        alert(text + "\n" + caller_line + "\n" + index + "\n" + clean);
    }

    static isOverlapping(x1: number, y1: number, w1: number, h1: number, x2: number, y2: number, w2: number, h2: number) {
        // Calculate the edges of the rectangles
        const left1 = x1;
        const right1 = x1 + w1;
        const top1 = y1;
        const bottom1 = y1 + h1;

        const left2 = x2;
        const right2 = x2 + w2;
        const top2 = y2;
        const bottom2 = y2 + h2;

        // Check if there is no overlap
        if (left1 >= right2 || left2 >= right1 || top1 >= bottom2 || top2 >= bottom1) {
            return null; // No overlap
        }

        // Calculate the overlap area
        const overlapX = Math.max(left1, left2);
        const overlapY = Math.max(top1, top2);
        const overlapWidth = Math.min(right1, right2) - overlapX;
        const overlapHeight = Math.min(bottom1, bottom2) - overlapY;

        return {
            x: overlapX,
            y: overlapY,
            width: overlapWidth,
            height: overlapHeight
        };
    }

    static resetAndRemoveAnimation(element: HTMLElement, class_name: string) {
        element.classList.remove(class_name);

        requestAnimationFrame(() => {
            element.classList.add(class_name); // Re-add the animation class to restart the animation

            function handleAnimationEnd() {
                element.classList.remove(class_name);
                element.removeEventListener('animationend', handleAnimationEnd);
            }

            element.removeEventListener('animationend', handleAnimationEnd);
            element.addEventListener('animationend', handleAnimationEnd, { once: true });
        })
    }
}

(window as any).Lib = Lib;

