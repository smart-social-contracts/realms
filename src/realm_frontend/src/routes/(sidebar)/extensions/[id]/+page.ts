import { error } from '@sveltejs/kit';
import { getExtension } from '$lib/extensions';
import type { PageLoad } from './$types';

export const load: PageLoad = ({ params }) => {
    const extension = getExtension(params.id);
    
    if (!extension) {
        throw error(404, {
            message: `Extension '${params.id}' not found`
        });
    }
    
    return {
        extension
    };
};
