// Minimal loadjs replacement - loads external scripts
// Used for loading YouTube/Vimeo SDKs (not needed for RtG preview)

export default function loadjs(urls, options = {}) {
    if (!Array.isArray(urls)) urls = [urls];
    
    const promises = urls.map(url => {
        return new Promise((resolve, reject) => {
            // Check if already loaded
            const existing = document.querySelector(`script[src="${url}"]`);
            if (existing) {
                resolve();
                return;
            }
            
            const script = document.createElement('script');
            script.src = url;
            script.async = true;
            script.onload = () => resolve();
            script.onerror = () => reject(new Error('Failed to load ' + url));
            document.head.appendChild(script);
        });
    });
    
    return Promise.all(promises).then(
        () => { if (options.success) options.success(); },
        (err) => { if (options.error) options.error(err); }
    );
}