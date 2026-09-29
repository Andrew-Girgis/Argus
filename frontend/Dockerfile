FROM node:20-bookworm-slim

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

EXPOSE 5173

HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=5 \
    CMD ["node", "-e", "fetch('http://127.0.0.1:5173').then(r => { if (!r.ok) process.exit(1) }).catch(() => process.exit(1))"]

CMD ["npm", "run", "dev", "--", "--host"]
