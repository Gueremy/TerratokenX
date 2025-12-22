document.addEventListener("DOMContentLoaded", function() {
    const whatsappButton = document.createElement("a");
    whatsappButton.href = "https://wa.me/1234567890?text=Hello%20I%20would%20like%20to%20make%20a%20reservation.";
    whatsappButton.target = "_blank";
    whatsappButton.style.position = "fixed";
    whatsappButton.style.bottom = "20px";
    whatsappButton.style.right = "20px";
    whatsappButton.style.backgroundColor = "#25D366";
    whatsappButton.style.color = "white";
    whatsappButton.style.borderRadius = "50%";
    whatsappButton.style.width = "60px";
    whatsappButton.style.height = "60px";
    whatsappButton.style.display = "flex";
    whatsappButton.style.alignItems = "center";
    whatsappButton.style.justifyContent = "center";
    whatsappButton.style.boxShadow = "0 2px 10px rgba(0, 0, 0, 0.3)";
    whatsappButton.style.zIndex = "1000";
    whatsappButton.innerHTML = "<img src='/static/reservations/images/whatsapp-icon.png' alt='WhatsApp' style='width: 30px; height: 30px;'>";

    document.body.appendChild(whatsappButton);
});