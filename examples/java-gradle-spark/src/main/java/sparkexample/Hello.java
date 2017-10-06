package sparkexample;

import static spark.Spark.get;
import static spark.Spark.port;

public class Hello {

    public static void main(String[] args) {
        port(8080);
        get("/", (req, res) -> {
            return "hello from sparkjava.com";
        });
    }

}
