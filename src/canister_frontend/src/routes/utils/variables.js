export const imgDir = 'assets';

/** @type {(x:string) => string} */
export const avatarPath = (src) => imgDir + '/users/' + src;

/** @type {(x:string, ...y:string[]) => string} */
export const imagesPath = (src) => [imgDir + '/images', src].filter(Boolean).join('/');
