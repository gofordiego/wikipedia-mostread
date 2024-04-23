function DatePicker({ title, formattedDate, onDateChange }: {
    title: string,
    formattedDate: string,
    onDateChange: (formattedDate: string) => void
}) {
    return (
        <label>
            <strong>{title}</strong>

            <input
                type="date"
                value={formattedDate}
                onChange={e => onDateChange(e.target.value)}
            />
        </label>
    )
}


export default DatePicker;