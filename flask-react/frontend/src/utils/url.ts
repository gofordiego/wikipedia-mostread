export function buildURL(host: string, uri: string, params: { [key: string]: string } = {}): string | undefined {
    const encodedComponents = Object.keys(params).map((key) => {
        const safeValue = encodeURIComponent(params[key])
        return `${key}=${safeValue}`
    }).join('&');

    let encodedURI = uri;
    if (encodedComponents.length) {
        encodedURI += `?${encodedComponents}`;
    }

    try {
        return new URL(encodedURI, host).toString();
    } catch (error) {
        console.error('buildURL error', error)
        return;
    }
}
