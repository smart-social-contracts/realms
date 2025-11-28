export const imgDir = 'images';

/** @type {(x:string) => string} */
export const avatarPath = (src) => imgDir + '/users/' + src;

/** @type {(x:string, ...y:string[]) => string} */
export const imagesPath = (src) => [imgDir, src].filter(Boolean).join('/');
