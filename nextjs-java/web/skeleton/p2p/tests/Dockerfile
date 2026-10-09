FROM docker.io/node:26.10.0-bookworm-slim AS node-runtime
FROM mcr.microsoft.com/playwright:v1.63.0-noble
COPY --from=node-runtime /usr/local/ /usr/local/
RUN npm install --global @yarnpkg/cli-dist@4.18.1
WORKDIR /app
COPY package.json yarn.lock .yarnrc.yml ./
RUN yarn install --immutable --mode=skip-build
COPY run.mjs ./
USER 1000:1000
CMD ["node", "run.mjs"]
