import { initializeCommon } from "./common.js";

document.addEventListener("DOMContentLoaded", async () => {
  const config = await initializeCommon();
  const price = document.querySelector("#business-price");
  const checkout = document.querySelector("#business-checkout");
  const enterprise = document.querySelector("#enterprise-contact");
  const contact = document.querySelector("#contact-link");
  if (config.business_price_label) price.textContent = config.business_price_label;
  if (config.business_checkout_url) {
    checkout.href = config.business_checkout_url;
    checkout.target = "_blank";
    checkout.rel = "noopener noreferrer";
    checkout.textContent = "安全な決済画面へ";
  } else if (config.contact_email) {
    checkout.href = `mailto:${config.contact_email}?subject=${encodeURIComponent("World Data Lens 法人向けパックの相談")}`;
  }
  const contactUrl = config.enterprise_contact_url || (config.contact_email ? `mailto:${config.contact_email}?subject=${encodeURIComponent("World Data Lens カスタム調査の相談")}` : "#contact");
  enterprise.href = contactUrl;
  contact.href = contactUrl;
  if (config.contact_email) contact.textContent = config.contact_email;
});
