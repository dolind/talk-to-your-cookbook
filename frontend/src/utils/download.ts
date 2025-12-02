export function downloadBlob(blob, fileName) {
    const url = window.URL.createObjectURL(
        blob.data ? new Blob([blob.data]) : new Blob([blob])
    );

    const a = document.createElement("a");
    a.href = url;
    a.download = fileName;
    a.style.display = "none";
    document.body.appendChild(a);

    a.click(); // trigger download
    a.remove();

    window.URL.revokeObjectURL(url);
}
