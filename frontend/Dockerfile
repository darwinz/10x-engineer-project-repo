FROM node:22-slim

WORKDIR /app

# Install dependencies first so this layer is cached unless package.json changes
COPY package.json package-lock.json ./
RUN npm install

# Copy application code
COPY . .

# Run as a non-root user rather than the image's default root. chown
# node_modules explicitly (not just root's default ownership from `npm
# install` above) since docker-compose's anonymous volume for it is seeded
# from this image — without this, Vite's dependency cache can't write into
# node_modules/.vite as appuser.
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 5173

# --host binds to 0.0.0.0 so the dev server is reachable from outside the
# container; `vite` alone binds to localhost only.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
