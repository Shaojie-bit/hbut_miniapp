export default {
    async fetch(request, env, ctx) {
        if (request.method !== "POST") return new Response("Proxy is running", { status: 200 });
        try {
            const payload = await request.json();
            const { target_url, method = "GET", headers = {}, body = null } = payload;

            const proxyReq = new Request(target_url, {
                method: method,
                headers: headers,
                body: body ? body : null,
                redirect: "manual" // 禁止自动重定向，手动处理以便获取 Cookie
            });

            const response = await fetch(proxyReq);

            // 处理二进制 Body (Base64)
            const buffer = await response.arrayBuffer();
            let binary = '';
            const bytes = new Uint8Array(buffer);
            const len = bytes.byteLength;
            for (let i = 0; i < len; i++) {
                binary += String.fromCharCode(bytes[i]);
            }
            const base64String = btoa(binary);
            // --- 关键修改：完整保留 Headers (尤其是 Set-Cookie) ---
            // 将 Headers 转换为数组形式，避免同名 Header 被覆盖
            const headersList = [];
            for (const [key, value] of response.headers) {
                headersList.push([key, value]);
            }
            // 对于 Set-Cookie，Cloudflare 可能会合并，也可能分开。
            // 使用 headers.get('set-cookie') 有时会得到合并的字符串
            // 但为了保险，我们直接遍历 Headers 对象。
            // 如果 Cloudflare 自动合并了 Set-Cookie，这种方式也能拿到合并后的值。
            // ---------------------------------------------------

            return new Response(JSON.stringify({
                status: response.status,
                headers_list: headersList, // 新字段：数组格式的 Headers
                body_base64: base64String
            }), {
                headers: { "Content-Type": "application/json" }
            });

        } catch (e) {
            return new Response(JSON.stringify({ error: e.toString() }), { status: 500 });
        }
    }
};