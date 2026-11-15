function confirmCancel() {
    return window.confirm("Are you sure you want to cancel this ticket?");
}
document.addEventListener("DOMContentLoaded", () => {
    const date = document.querySelector('input[name="travel_date"]');
    if (date) {
        const now = new Date();
        date.min = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
    }
});
