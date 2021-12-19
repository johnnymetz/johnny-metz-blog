FROM node:17
WORKDIR /app

# install dependencies
COPY package*.json ./
RUN npm install

# copy source code
COPY . .

# start server
CMD ["npm", "run", "dev"]
