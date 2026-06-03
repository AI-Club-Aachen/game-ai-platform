FROM oven/bun:1 AS build
WORKDIR /app

# Install dependencies
# We copy package.json and only install dependencies first to cache them
COPY package.json ./
# If you have a lockfile, copy it too. Since we are switching to bun, we might regenerate it.
# Check if pnpm-lock.yaml or package-lock.json exists and copy if needed, 
# but bun install works with package.json alone.
RUN bun install

ARG VITE_API_URL
ARG MAX_TURN_TIME_LIMIT_SECONDS
ENV VITE_API_URL=$VITE_API_URL
ENV MAX_TURN_TIME_LIMIT_SECONDS=$MAX_TURN_TIME_LIMIT_SECONDS

# Copy source code
COPY . .

RUN bun run build

FROM build AS dev

# Expose Vite dev server port
EXPOSE 3000

CMD ["bun", "run", "dev", "--host", "0.0.0.0"]

FROM nginx:1.27-alpine AS production

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose Dokploy/Traefik target port
EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
