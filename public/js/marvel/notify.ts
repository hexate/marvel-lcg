import { Setting } from './settings.js'
// @ts-ignore
import { Notifications } from '../lib/notifications.js'

export class Notify {

    static notis = new Notifications(document.querySelector(".notifications"));

    static {
        const logo_code = [
            'KeyI', 'KeyR', 'KeyE', 'KeyF',
            'KeyR', 'KeyI', 'KeyX', 'KeyS',
        ];

        let logo_index = 0;
        let logo_code_string = ""

        document.addEventListener('keydown', (event) => {
            if (event.code === logo_code[logo_index]) {
                logo_index++;
                logo_code_string += event.key
                if (logo_index === logo_code.length) {
                    Notify.create("", "", `${logo_code_string.charAt(0).toUpperCase() + logo_code_string.slice(1)} (c)`)
                    logo_index = 0;
                    logo_code_string = ""
                }
            } else {
                logo_index = 0;
                logo_code_string = ""
            }
        });
    }

    static showResponse(text: string) {
        Notify.create("RESPONSE", "debug", text, 2)
    }

    static showAchievement(text: string) {
        if( !Setting.show_achievement ) {
            return
        }
        let div = document.querySelector('#achievement-bar') as HTMLElement
        div.classList.remove('remove')
        div.classList.add('enter')
        div.innerHTML = text
        setTimeout(() => {
            div.classList.remove('enter')
            div.classList.add('remove')
        }, 2000);
    }

    static pause() {
        Notify.notis.pause()
    }

    static unpause() {
        Notify.notis.unpause()
    }

    static create(
        title = "",
        ex_class_name = "",
        description = "",
        duration = 4,
        destroyOnClick = true,
        clickFunction = undefined,
    ) {
        Notify.notis.create(
            title,
            ex_class_name,
            description,
            duration,
            destroyOnClick,
            clickFunction
        );
    }

    static showStatisticsText(text: string) {
        if( !Setting.is_debug && Setting.statistics_off ) {
            return
        }

        let class_name = 'statistics'
        let div_test = `<span class='${class_name}'>${text}</span>`
        // No title. Every one of these toasts said "STATISTIC" over a line that already reads
        // "<card art> Enters Play x1", so the header named the category of the message rather than
        // telling you anything about the event. The empty string is handled in `notification.css`,
        // which collapses an empty `.notititle` rather than leaving its padding behind.
        Notify.create("", "", div_test)
    }

    static showStatistics(card_id: string, text: string, count: number) {
        if( !Setting.is_debug && Setting.statistics_first && count != 1 ) {
            return
        }
        if( ["PutIntoPlay", "Attached", "Hero"].includes(text)  ) {
            text = "Enters Play"
        }
        // if( ["Discard"].includes(text)  ) {
        //     text = "Defeated"
        // }

        let notify_text = `<img class='statistics-notify-img' style='--bg-image-true: url("${card_id}")'></img>  ${text} x${count}`

        Notify.showStatisticsText(notify_text)
    }

    static showCommand(text: string) {
        Notify.create("COMMAND", "", text, 2)
    }
}
