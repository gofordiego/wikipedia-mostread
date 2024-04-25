import { WIKIPEDIA_LANGUAGES } from '../utils/constants'


type WikipediaLanguage = {
    code: string,
    name: string,
}


function LanguageSelect({ selectedLanguageCode, onLanguageChange }: {
    selectedLanguageCode: string,
    onLanguageChange: (languageCode: string) => void
}) {
    const optionItems = WIKIPEDIA_LANGUAGES.map((language: WikipediaLanguage) => {
        return (
            <option key={language.code} value={language.code} >{language.name}</option>
        )
    });

    return (
        <label>
            <strong>Language</strong>

            <select
                className="py-2"
                value={selectedLanguageCode}
                onChange={e => onLanguageChange(e.target.value)}
            >
                {optionItems}
            </select>
        </label>
    )
}


export default LanguageSelect;