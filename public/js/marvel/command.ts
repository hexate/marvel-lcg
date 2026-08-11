import { Cards } from "./cards.js";
import { Notify } from "./notify.js";

export class Command {

    private static newWindow: Window|null = null

    static setLastClickCard(card_div: HTMLElement) {
        if( Command.newWindow && !Command.newWindow.closed ) {
            const card = Cards.getCard(Number(card_div.dataset.id!))!
            const data = {
                type: 'setLastClickCard',
                card_object_id: card_div.dataset.id,
                card_id: card.card_id,
                card_name: card.name,
            };
            Command.newWindow.postMessage(data, '*')
            Command.newWindow.focus();
            return true
        }
        else {
            return false
        }
    }

    static async saveLocal() {
        const response_block_thread = await fetch("save_local?");
        const text = await response_block_thread.text();
        // const text = "A"
        // prompt(`Your save file has been saved in:`, text)
        // Unrouted paths fall through to the image handler, which answers 200 with a JPEG. Without
        // this check a save that never happened reports the image bytes as its file path.
        if (!response_block_thread.ok) {
            Notify.showCommand(`Save failed: ${text}`)
            return
        }
        Notify.showCommand(`Your save file has been saved in: ${text}`)
    }

    static async uploadSave(save_type: "Bug"|"Crash"|"Share", comment: string="") {
        if( Command.newWindow && !Command.newWindow.closed ) {
            Command.newWindow.close()
        }
        // window.open(`report.html?save_type=${save_type}`, "newWindow", "width=400,height=320");
        // Open the new window
        Command.newWindow = window.open(`report`, "newWindow", "width=400,height=320")!;

        const data = {
            type: 'uploadSave',
            save_type: save_type,
            comment: comment
        };

        // Send data to the new window once it has loaded
        Command.newWindow.onload = () => {
            Command.newWindow!.postMessage(data, '*'); // Use '*' to allow any origin or specify the target origin
        };
    }
}