FROM node:20-alpine AS deps
WORKDIR /app
COPY web/package.json web/package-lock.json ./
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY web ./

ARG NEXT_PUBLIC_TUTOR_API_URL
ARG NEXT_PUBLIC_PIPECAT_URL
ARG NEXT_PUBLIC_TALK_PIPECAT_URL
ARG BACKEND_HOST=http://127.0.0.1
ARG BACKEND_PORT=8000
ARG VOICE_HOST=http://127.0.0.1
ARG VOICE_PORT=7860
ARG TALK_HOST=http://127.0.0.1
ARG TALK_PORT=7863

ENV NEXT_PUBLIC_TUTOR_API_URL=$NEXT_PUBLIC_TUTOR_API_URL \
    NEXT_PUBLIC_PIPECAT_URL=$NEXT_PUBLIC_PIPECAT_URL \
    NEXT_PUBLIC_TALK_PIPECAT_URL=$NEXT_PUBLIC_TALK_PIPECAT_URL \
    BACKEND_HOST=$BACKEND_HOST \
    BACKEND_PORT=$BACKEND_PORT \
    VOICE_HOST=$VOICE_HOST \
    VOICE_PORT=$VOICE_PORT \
    TALK_HOST=$TALK_HOST \
    TALK_PORT=$TALK_PORT \
    NEXT_TELEMETRY_DISABLED=1

RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

CMD ["node", "server.js"]
