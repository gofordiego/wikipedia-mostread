import { buildURL } from './utils';


namespace BackendAPI {

    //  MARK: FetchResults type

    export interface FetchResults<T, E> {
        data?: T[];
        errors?: E[];
        request_error?: string;
    }


    // MARK: FetchError type

    export enum FetchErrorType {
        URL,  // Malformed URL
        Response,  // Non-OK fetch response
        Request,  // Invalid API params (MostReadArticlesResponse.request_error)
    }

    export type FetchError = {
        errorType: FetchErrorType,
        message: string,
    };

    export function computeFetchErrorType<T, E>(url: string | undefined, responseError: string, results: FetchResults<T, E>): FetchError | null {
        let errorType: FetchErrorType | null = null
        let message = ""
        if (url === undefined) {
            errorType = FetchErrorType.URL;
            message = "Invalid Backend API Server"
        } else if (results.request_error) {
            errorType = FetchErrorType.Request;
            message = results.request_error
        } else if (responseError) {
            errorType = FetchErrorType.Response;
            message = responseError
        }
        return errorType !== null ? { errorType, message } : null
    }


    // MARK: - /most_read_articles endpoint

    type MostReadArticlesParams = {
        lang_code: string,
        start: string,
        end: string
    };

    export function buildMostReadArticlesURL(host: string, params: MostReadArticlesParams): string | undefined {
        return buildURL(host, '/most_read_articles', params);
    }
}


export default BackendAPI;