document.addEventListener("DOMContentLoaded", () => {
    const forms = document.querySelectorAll("form");
  
    forms.forEach(form => {
      form.addEventListener("submit", (e) => {
        const password = form.querySelector('input[type="password"]');
        if (password && password.value.length < 8) {
          alert("Password must be at least 8 characters long.");
          e.preventDefault();
        }
      });
    });
  });