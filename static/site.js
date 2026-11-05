// Contact links (href="#contact") open an email. The address is assembled here,
// only on click, so it never appears in the page source for scrapers to harvest.
document.addEventListener("click", (e) => {
	const contact = e.target.closest('a[href="#contact"]');
	if (contact) {
		e.preventDefault();
		const user = ["seungki", "tom", "chung"].join("");
		location.href = "mailto:" + user + "@" + ["gmail", "com"].join(".");
		return;
	}

	// Click-to-zoom images (Cargo's "quick view")
	const img = e.target.closest("media-item.zoomable img");
	if (img) {
		const box = document.createElement("div");
		box.className = "lightbox";
		box.innerHTML = `<img src="${img.src}" alt="">`;
		const close = () => { box.remove(); removeEventListener("keydown", onKey); };
		const onKey = (k) => k.key === "Escape" && close();
		box.addEventListener("click", close);
		addEventListener("keydown", onKey);
		document.body.append(box);
	}
});
