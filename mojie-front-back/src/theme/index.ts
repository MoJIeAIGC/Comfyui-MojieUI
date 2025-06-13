import {ElMessage} from "element-plus";


export const getLevel = function (color: string, level: number) {
    let reg = /^\#?[0-9A-Fa-f]{6}$/;
    if (!reg.test(color)) {
        ElMessage.error('hex color error.');
        return '';
    }
    //转rgb

    let r = parseInt(color.slice(1, 3), 16);
    let g = parseInt(color.slice(3, 5), 16);
    let b = parseInt(color.slice(5, 7), 16);

    const mix = (val) => {
        return Math.floor((255 - val) * level + val)
    }
    let rgb = {
        r: mix(r),
        g: mix(g),
        b: mix(b),
    }
    const toHex = () => {
        let {r, g, b} = rgb;
        let hex = "#";
        let hexR = r.toString(16);
        let hexG = g.toString(16);
        let hexB = b.toString(16);

        if (hexR.length === 1)
            hexR = "0" + r;
        if (hexG.length === 1)
            hexG = "0" + g;
        if (hexB.length === 1)
            hexB = "0" + b;

        return "#" + hexR + hexG + hexB;
    }

    //转hex
    return toHex()

}


export const hexToRgb = function (hex: string) {

    let rgb = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return rgb ? [
        parseInt(rgb[1], 16),
        parseInt(rgb[2], 16),
        parseInt(rgb[3], 16)
    ] : null;
}

export const setPrimaryColor = function (color: string) {
    let map = {
        "--el-color-primary": color,
        "--primary-color": color,
        // "--sidebar-active-color": `rgba(${hexToRgb(color).join(',')},0.6)`
    }
    //其他颜色
    for (let i = 1; i <= 9; i++) {
        map[`--el-color-primary-light-${i}`] = getLevel(color, i / 10)
    }
    for (let key in map) {
        document.documentElement.style.setProperty(key, map[key]);
    }
}