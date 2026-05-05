const CHINESE_REGION_CODES = new Set(["CN", "HK", "MO", "TW"]);

function readCookie(cookieHeader, name) {
  if (!cookieHeader) {
    return "";
  }

  const cookies = cookieHeader.split(";").map((cookie) => cookie.trim());
  const prefix = `${name}=`;
  const match = cookies.find((cookie) => cookie.startsWith(prefix));

  return match ? decodeURIComponent(match.slice(prefix.length)) : "";
}

export async function onRequest(context) {
  const { request } = context;
  const url = new URL(request.url);

  if (url.pathname !== "/") {
    return context.next();
  }

  const savedLanguage = readCookie(request.headers.get("Cookie"), "slite_language");

  if (savedLanguage === "en") {
    return Response.redirect(`${url.origin}/en/`, 302);
  }

  if (savedLanguage === "zh") {
    return context.next();
  }

  const country = request.cf?.country || request.headers.get("CF-IPCountry") || "";

  if (!CHINESE_REGION_CODES.has(country.toUpperCase())) {
    return Response.redirect(`${url.origin}/en/`, 302);
  }

  return context.next();
}
