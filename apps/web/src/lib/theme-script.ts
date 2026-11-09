/** Key the owner's choice is kept under in this browser: "light", "dark", or absent/"system" to follow the machine. */
export const THEME_KEY = "theme";

/** Runs in <head> before the first paint, so a dark page never flashes white. No import: the server layout renders it as text. */
export const THEME_SCRIPT = `var s;try{s=localStorage.getItem("${THEME_KEY}")}catch(e){}document.documentElement.dataset.theme=s==="dark"||(s!=="light"&&matchMedia("(prefers-color-scheme: dark)").matches)?"dark":"light";`;
