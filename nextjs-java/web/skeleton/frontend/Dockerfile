FROM docker.io/node:26.10.0-alpine3.24 AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1 YARN_NODE_LINKER=node-modules YARN_ENABLE_SCRIPTS=true
RUN npm install --global @yarnpkg/cli-dist@4.18.1
COPY package.json yarn.lock .yarnrc.yml ./
RUN yarn install --immutable
COPY . .
ARG UNIT_TEST_NONCE=manual
RUN test -n "$UNIT_TEST_NONCE" && yarn lint && yarn test --runInBand && yarn build
FROM docker.io/node:26.10.0-alpine3.24 AS runtime
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
USER 1000:1000
EXPOSE 3000 8081
CMD ["node", "server.js"]
