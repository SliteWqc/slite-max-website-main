document.documentElement.classList.add("js");

const revealNodes = document.querySelectorAll(".reveal");

if ("IntersectionObserver" in window) {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) {
          return;
        }

        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      });
    },
    {
      threshold: 0.18,
      rootMargin: "0px 0px -8% 0px"
    }
  );

  revealNodes.forEach((node) => observer.observe(node));
} else {
  revealNodes.forEach((node) => node.classList.add("is-visible"));
}

document.querySelectorAll(".language-switch[data-language]").forEach((link) => {
  link.addEventListener("click", () => {
    const language = link.dataset.language;

    if (!language) {
      return;
    }

    document.cookie = `slite_language=${language}; Path=/; Max-Age=31536000; SameSite=Lax`;
  });
});
