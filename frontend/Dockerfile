ARG NODE_IMAGE=mirror.gcr.io/library/node:20-alpine
FROM ${NODE_IMAGE} AS base

FROM base AS deps
WORKDIR /app
COPY package.json package-lock.json ./
# npm cache mount keeps downloaded packages between builds → no re-download even if
# this layer rebuilds (e.g. after a full builder prune or a flaky network).
RUN --mount=type=cache,target=/root/.npm \
    npm ci --no-audit --no-fund && test -x node_modules/.bin/next

FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
ARG BACKEND_URL=http://localhost:8000
ENV BACKEND_URL=$BACKEND_URL
RUN npm run build

FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME=0.0.0.0
CMD ["node", "server.js"]
