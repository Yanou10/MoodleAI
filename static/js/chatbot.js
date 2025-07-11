(function () {
  const bubble = document.createElement("div");
  bubble.innerHTML = "💬";
  bubble.id = "chat-bubble";
  Object.assign(bubble.style, {
    position: "fixed",
    bottom: "20px",
    right: "20px",
    background: "#007bff",
    color: "#fff",
    fontSize: "24px",
    padding: "12px",
    borderRadius: "50%",
    cursor: "pointer",
    zIndex: 9999,
  });
  document.body.appendChild(bubble);

  let iframe = null;
  bubble.onclick = () => {
    if (iframe) {
      iframe.remove();
      iframe = null;
      return;
    }

    iframe = document.createElement("iframe");
    iframe.src = "/chat";  // Your assistant UI
    Object.assign(iframe.style, {
      position: "fixed",
      bottom: "80px",
      right: "20px",
      width: "400px",
      height: "500px",
      border: "1px solid #ccc",
      borderRadius: "10px",
      background: "#fff",
      zIndex: 9998,
    });
    document.body.appendChild(iframe);
  };
})();
