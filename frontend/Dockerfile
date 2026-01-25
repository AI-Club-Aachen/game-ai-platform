FROM oven/bun:1 AS base
WORKDIR /app

# Install dependencies
# We copy package.json and only install dependencies first to cache them
COPY package.json ./
# If you have a lockfile, copy it too. Since we are switching to bun, we might regenerate it.
# Check if pnpm-lock.yaml or package-lock.json exists and copy if needed, 
# but bun install works with package.json alone.
RUN bun install

# Copy source code
COPY . .

# Expose Vite port
EXPOSE 3000

# Start development server
CMD ["bun", "run", "dev", "--host"]
