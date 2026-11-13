function setupBudgetSlider(container) {
  const select = container.querySelector("select");
  const slider = container.querySelector('input[type="range"]');
  const output = container.querySelector("output");
  const buttons = container.querySelectorAll("[data-budget-option]");
  const options = Array.from(select.options);
  const updateBudget = () => {
    const option = options[Number(slider.value)];
    select.value = option.value;
    output.textContent = option.textContent.trim();
    slider.setAttribute("aria-valuetext", output.textContent);
    buttons.forEach((button, index) => {
      button.setAttribute("aria-pressed", String(index === Number(slider.value)));
    });
  };
  slider.max = String(options.length - 1);
  slider.value = String(Math.max(0, select.selectedIndex));
  slider.addEventListener("input", updateBudget);
  buttons.forEach((button, index) => {
    button.addEventListener("click", () => {
      slider.value = String(index);
      updateBudget();
    });
  });
  select.hidden = true;
  updateBudget();
  return updateBudget;
}

function setupLocationAutocomplete(container) {
  const input = container.querySelector("[data-location-input]");
  const id = container.querySelector("[data-location-id]");
  const suggestions = container.querySelector("[data-location-suggestions]");
  const hint = container.querySelector("[data-location-hint]");
  let searchId = 0;
  const setLocation = (value, label) => {
    searchId++;
    id.value = value || "";
    input.value = label || "";
    input.setCustomValidity(value ? "" : "Choose a valid location from the suggestions.");
    suggestions.replaceChildren();
    hint.textContent = value ? "Location selected." : "Type a city or neighborhood and choose a suggestion.";
  };
  setLocation(id.value, input.value);
  input.addEventListener("input", async () => {
    const currentSearch = ++searchId;
    const text = input.value.trim();
    id.value = "";
    input.setCustomValidity("Choose a valid location from the suggestions.");
    suggestions.replaceChildren();
    hint.textContent = "Type a city or neighborhood and choose a suggestion.";
    if (!text) return;
    try {
      const query = text.split(",")[0].trim();
      const response = await fetch(container.dataset.locationsUrl + "?q=" + encodeURIComponent(query));
      if (!response.ok) throw new Error();
      const matches = await response.json();
      if (currentSearch !== searchId || input.value.trim() !== text) return;
      for (const location of matches) {
        const label = location.city + ", " + location.state;
        if (label.toLowerCase() === text.toLowerCase()) {
          setLocation(location.location_id, label);
          return;
        }
        const button = document.createElement("button");
        button.type = "button";
        button.className = "my-profile-secondary";
        button.textContent = label;
        button.addEventListener("click", () => {
          setLocation(location.location_id, label);
          input.focus();
        });
        suggestions.append(button);
      }
      hint.textContent = matches.length ? "Choose a matching location from the suggestions."
        : "No matching locations. Try another city or neighborhood.";
    } catch (error) {
      if (currentSearch === searchId) hint.textContent = "Could not load locations. Please try typing again.";
    }
  });
  return setLocation;
}

function setupPhotoPreview(form, photo, nameInput) {
  const input = form.querySelector('input[name="profile_picture"]');
  const remove = form.querySelector('input[name="remove_picture"]');
  const clearButton = form.querySelector("[data-clear-photo]");
  const image = photo.querySelector("img");
  const initial = photo.querySelector("[data-photo-initial]");
  const savedSource = image.getAttribute("src");
  const savedInitial = initial.textContent;
  let previewUrl = null;
  const restorePhoto = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = null;
    if (savedSource) image.src = savedSource;
    else image.removeAttribute("src");
    image.hidden = !savedSource;
    initial.hidden = Boolean(savedSource);
    initial.textContent = savedInitial;
    input.setCustomValidity("");
  };
  const updateInitial = () => {
    if (image.hidden) initial.textContent = nameInput.value.trim().charAt(0).toUpperCase() || "?";
  };
  nameInput.addEventListener("input", updateInitial);
  form.addEventListener("reset", () => {
    input.disabled = false;
    if (clearButton) clearButton.hidden = true;
    restorePhoto();
  });
  if (clearButton) {
    clearButton.addEventListener("click", () => {
      input.value = "";
      input.dispatchEvent(new Event("change"));
      input.focus();
    });
  }
  if (remove) {
    remove.addEventListener("change", () => {
      restorePhoto();
      input.value = "";
      input.disabled = remove.checked;
      image.hidden = remove.checked || !savedSource;
      initial.hidden = !image.hidden;
      updateInitial();
    });
  }
  input.addEventListener("change", () => {
    restorePhoto();
    updateInitial();
    const file = input.files[0];
    if (clearButton) clearButton.hidden = !file;
    if (!file) return;
    if (!["image/jpeg", "image/png"].includes(file.type) || !file.size || file.size > 2 * 1024 * 1024) {
      input.setCustomValidity("Choose a non-empty JPEG or PNG image, up to 2 MB.");
      input.reportValidity();
      return;
    }
    previewUrl = URL.createObjectURL(file);
    image.src = previewUrl;
    image.hidden = false;
    initial.hidden = true;
    photo.scrollIntoView({ block: "nearest", behavior: "smooth" });
  });
  image.addEventListener("error", () => {
    if (!previewUrl) return;
    restorePhoto();
    updateInitial();
    input.setCustomValidity("Choose a valid JPEG or PNG image.");
    input.reportValidity();
  });
  window.addEventListener("pagehide", () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  });
}
