import { buildURL } from './utils';


type MostReadArticlesParams = {
    lang_code: string,
    start: string,
    end: string
};


class BackendAPI {
    static buildMostReadArticlesURL(host: string, params: MostReadArticlesParams): string | undefined {
        return buildURL(host, '/most_read_articles', params);
    }
}


export default BackendAPI;