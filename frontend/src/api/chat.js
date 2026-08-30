import axios from "axios"


const request = axios.create({

    baseURL:"/api"

})


export function chat(question){

    return request.post(
        "/chat",
        {
            user_id:"demo",
            question:question
        }
    )

}

export function chatStream(
    question,
    onToken,
    onMetadata
) {
    fetch(
        "/api/chat/stream",
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                user_id: "demo",
                question
            })
        }
    )
    .then(response => {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        // 用于存储上一个未完成的数据包
        let buffer = "";

        function read() {
            reader.read()
                .then(({ done, value }) => {
                    if (done) return;

                    // 1. 将新数据追加到缓冲区
                    buffer += decoder.decode(value, { stream: true });

                    // 2. 按双换行符切分完整事件
                    let events = buffer.split("\n\n");
                    
                    // 3. 保留最后一个不完整的事件（可能只收到一半）
                    buffer = events.pop() || "";

                    // 4. 处理每个完整事件
                    events.forEach(event => {
                        if (!event.trim()) return;

                        let lines = event.split("\n");
                        let eventType = "";
                        let data = "";

                        lines.forEach(line => {
                            if (line.startsWith("event:")) {
                                eventType = line.replace("event:", "").trim();
                            }
                            if (line.startsWith("data:")) {
                                data = line.replace("data:", "").trim();
                            }
                        });

                        // 触发对应的回调
                        if (eventType === "token") {
                            onToken(data);
                        }
                        if (eventType === "metadata") {
                            try {
                                onMetadata(JSON.parse(data));
                            } catch (e) {
                                console.warn("解析 metadata 失败:", data, e);
                            }
                        }
                    });

                    // 5. 继续读取下一块数据
                    read();
                });
        }

        read();
    })
    .catch(err => {
        console.error("chatStream 连接失败:", err);
    });
}