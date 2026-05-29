export async function onRequestPost(context) {
  const { env, request } = context;

  let email;
  try {
    const contentType = request.headers.get("content-type") || "";

    if (contentType.includes("application/json")) {
      const body = await request.json();
      email = body.email;
    } else if (contentType.includes("application/x-www-form-urlencoded")) {
      const body = await request.text();
      const params = new URLSearchParams(body);
      email = params.get("email");
    } else {
      // Fallback: try both
      const body = await request.text();
      try {
        const json = JSON.parse(body);
        email = json.email;
      } catch {
        const params = new URLSearchParams(body);
        email = params.get("email");
      }
    }
  } catch (err) {
    return new Response(JSON.stringify({ error: "Failed to parse request" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  if (!email || !email.includes("@")) {
    return new Response(JSON.stringify({ error: "Valid email required" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  // Normalize email
  email = email.trim().toLowerCase();

  try {
    // Insert into D1 — ignore duplicates
    await env.agentscope_waitlist.prepare(
      "INSERT OR IGNORE INTO waitlist (email, source) VALUES (?, 'landing_page')"
    ).bind(email).run();

    return new Response(JSON.stringify({ ok: true, message: "You're on the list!" }), {
      status: 200,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      },
    });
  } catch (err) {
    console.error("D1 error:", err);
    return new Response(JSON.stringify({ error: "Failed to save email" }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
}

// Handle CORS preflight
export async function onRequestOptions() {
  return new Response(null, {
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    },
  });
}
